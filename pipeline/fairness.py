"""Bias metrics over probe embeddings: label parity across groups, attribute recoverability,
and how much each node centroid points along an attribute direction."""
import argparse
from pathlib import Path

import numpy as np

from pipeline.build_index import MIN_IMAGES, normalize
from pipeline.debias import RACE_GROUPS, align_by_path, apply, fit_rows, suffix
from pipeline.evaluate import accuracy, loo_sims
from pipeline.logreg import cv_accuracy
from pipeline.train_head import best_l2, cv_scores, group_weights, train, zscore
from server.match import IMAGE_WEIGHT, PRIOR_WEIGHT, TEXT_WEIGHT

DATA = Path(__file__).resolve().parent.parent / "data"
OVER_TOP = 10
# name, scorer (centroid | head | head_rw), treatment (none | prompt | leace), masked
CONFIGS = [
    ("centroid", "centroid", "none", False),
    ("centroid+prompt", "centroid", "prompt", False),
    ("centroid+leace", "centroid", "leace", False),
    ("centroid+mask", "centroid", "none", True),
    ("centroid+mask+leace", "centroid", "leace", True),
    ("head", "head", "none", False),
    ("head_rw", "head_rw", "none", False),
    ("head_rw+leace", "head_rw", "leace", False),
    ("head_rw+mask+leace", "head_rw", "leace", True),
]


def parity(top1: np.ndarray, groups: np.ndarray, n_nodes: int) -> dict:
    """Top-1 label distribution per group; max total-variation distance between any two groups;
    per group the nodes most over-represented relative to the pooled distribution."""
    pooled = np.bincount(top1, minlength=n_nodes) / len(top1)
    per = {g: np.bincount(top1[groups == g], minlength=n_nodes) / (groups == g).sum() for g in np.unique(groups)}
    keys = list(per)
    max_tvd = max((0.5 * np.abs(per[a] - per[b]).sum() for a in keys for b in keys if a < b), default=0.0)
    over = {}
    for g, dist in per.items():
        ratio = dist / np.maximum(pooled, 1e-9)
        idx = np.argsort(-ratio * (dist > 0))[:OVER_TOP]
        over[g] = [(int(i), float(ratio[i])) for i in idx if dist[i] > 0]
    return {"max_tvd": float(max_tvd), "per_group": per, "over": over}


def parity_floor(top1: np.ndarray, groups: np.ndarray, n_nodes: int, seed: int = 0) -> float:
    """Max TVD when group labels are shuffled: what this probe size reads as parity by chance."""
    return parity(top1, np.random.default_rng(seed).permutation(groups), n_nodes)["max_tvd"]


def centroid_probe_scores(pvecs_raw: np.ndarray, sums: np.ndarray, z, P: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Probe scores by the served scorer: unit centroid, then projection, then centering (see
    server/match.Index). `z` holds the index arrays; `sums` are unprojected unit-vector sums."""
    project = lambda v: apply(v, P, b)
    mean_img, mean_txt = project(z["mean_img"][None])[0], project(z["mean_txt"][None])[0]
    q = project(pvecs_raw)
    img = normalize(q - mean_img) @ normalize(project(normalize(sums)) - mean_img).T
    txt = normalize(q - mean_txt) @ normalize(project(z["text_vecs"]) - mean_txt).T
    return np.where(z["counts"] > 0, IMAGE_WEIGHT * img + TEXT_WEIGHT * txt, txt) + PRIOR_WEIGHT * z["prior"]


def recoverability(vecs: np.ndarray, labels: np.ndarray) -> dict:
    counts = np.bincount(labels)
    return {"acc": cv_accuracy(vecs, labels, len(counts)), "chance": 1 / len(counts),
            "majority": float(counts.max() / counts.sum())}


def group_directions(vecs: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Orthonormal basis (k-1, d) spanning the differences between group means."""
    means = np.stack([vecs[labels == g].mean(0) for g in np.unique(labels)])
    diffs = means[1:] - means[0]
    q, _ = np.linalg.qr(diffs.T)
    return q.T.astype(np.float32)


def node_loading(centroids: np.ndarray, directions: np.ndarray) -> np.ndarray:
    return normalize(centroids) @ normalize(directions).T


TAG = ""  # set by --tag: evaluate index_TAG / image_vecs_TAG (e.g. a --crops build) in the unmasked rows


def load_bundle(masked: bool):
    sfx = suffix(TAG, masked)
    paths = [DATA / f"index{sfx}.npz", DATA / f"image_vecs{sfx}.npz", DATA / f"probe{sfx}.npz"]
    if not all(p.exists() for p in paths):
        return None
    return tuple(np.load(p) for p in paths)


def treatment_map(name: str, masked: bool, d: int):
    if name == "none":
        return np.eye(d, dtype=np.float32), np.zeros(d, np.float32)
    t = np.load(DATA / f"debias_{name}{suffix(TAG, masked and name == 'leace')}.npz")
    return t["P"], t["b"]


def run_config(scorer: str, treatment: str, masked: bool, attrs) -> dict | None:
    """Score reference images (leave-one-out or out-of-fold) and probe faces under one
    configuration; return the report numbers for it."""
    bundle = load_bundle(masked)
    if bundle is None:
        return None
    z, img, probe = bundle
    slugs = list(z["slugs"])
    owner_idx = np.array([slugs.index(o) for o in img["owner"]])
    P, b = treatment_map(treatment, masked, img["vecs"].shape[1])
    held = ~fit_rows(len(probe["race"]))  # LEACE was fitted on the other rows; measure out of sample
    praw, prace, pgender = probe["vecs"][held], probe["race"][held], probe["gender"][held]
    vecs, pvecs, text = apply(img["vecs"], P, b), apply(praw, P, b), apply(z["text_vecs"], P, b)
    counts, prior = z["counts"], z["prior"]
    mean_img, mean_txt = apply(z["mean_img"][None], P, b)[0], apply(z["mean_txt"][None], P, b)[0]
    txt_ref = normalize(vecs - mean_txt) @ normalize(text - mean_txt).T
    txt_probe = normalize(pvecs - mean_txt) @ normalize(text - mean_txt).T
    sums = np.zeros_like(z["centroids"]); np.add.at(sums, owner_idx, img["vecs"])  # unprojected, like build_index
    if scorer == "centroid":
        ref = loo_sims(img["vecs"], owner_idx, len(slugs), mean_img, lambda v: apply(v, P, b))
        ref_s = np.where(counts > 0, IMAGE_WEIGHT * ref + TEXT_WEIGHT * txt_ref, txt_ref) + PRIOR_WEIGHT * prior
        pro_s = centroid_probe_scores(praw, sums, z, P, b)
    else:
        w = group_weights(align_by_path(attrs["race"], load_bundle(False)[1]["path"], img["path"]), owner_idx) if scorer == "head_rw" else None
        l2 = best_l2(vecs, owner_idx, len(slugs), img["source"], w)
        ref_s = zscore(cv_scores(vecs, owner_idx, len(slugs), img["source"], w, l2))
        W, hb = train(vecs, owner_idx, len(slugs), w, l2)
        pro_s = zscore(pvecs @ W.T + hb)
        fallback = counts < MIN_IMAGES
        ref_s = np.where(fallback, zscore(txt_ref), ref_s) + PRIOR_WEIGHT * prior
        pro_s = np.where(fallback, zscore(txt_probe), pro_s) + PRIOR_WEIGHT * prior
    plain_w = 1 / counts[owner_idx]
    top1 = pro_s.argmax(1)
    race_par, gender_par = parity(top1, prace, len(slugs)), parity(top1, pgender, len(slugs))
    loading = node_loading(apply(normalize(sums), P, b), group_directions(pvecs, prace))
    return {"race_tvd": race_par["max_tvd"], "gender_tvd": gender_par["max_tvd"],
            "race_floor": parity_floor(top1, prace, len(slugs)), "gender_floor": parity_floor(top1, pgender, len(slugs)),
            "race_acc": recoverability(pvecs, prace)["acc"], "gender_acc": recoverability(pvecs, pgender)["acc"],
            "top1": accuracy(ref_s, owner_idx, plain_w, 1), "top5": accuracy(ref_s, owner_idx, plain_w, 5),
            "over": {RACE_GROUPS[g]: [(slugs[i], r) for i, r in v] for g, v in race_par["over"].items()},
            "loading": [(slugs[i], float(np.abs(loading[i]).max())) for i in np.argsort(-np.abs(loading).max(1))[:OVER_TOP]]}


def main(only: list[str] | None, tag: str = ""):
    global TAG
    TAG = tag
    attrs = np.load(DATA / f"reference_attrs{suffix(tag, False)}.npz")
    lines = ["| config | race TVD | gender TVD | race acc (chance 0.143) | gender acc (chance 0.5) | LOO top1 | LOO top5 |",
             "|---|---|---|---|---|---|---|"]
    if attrs["race_cv_acc"] < 0.6 or attrs["gender_cv_acc"] < 0.85:
        lines.insert(0, f"WARNING: attribute labels are noisy (race {attrs['race_cv_acc']:.2f}, gender {attrs['gender_cv_acc']:.2f}); "
                        "reweighted rows are unreliable\n")
    details = []
    floor_line = None
    for name, scorer, treatment, masked in CONFIGS:
        if only and name not in only:
            continue
        r = run_config(scorer, treatment, masked, attrs)
        if r is None:
            lines.append(f"| {name} | (missing masked data) | | | | | |")
            continue
        lines.append(f"| {name} | {r['race_tvd']:.3f} | {r['gender_tvd']:.3f} | {r['race_acc']:.3f} | {r['gender_acc']:.3f} | "
                     f"{r['top1']:.3f} | {r['top5']:.3f} |")
        print(lines[-1])
        floor_line = floor_line or (f"Parity is measured on the probe half LEACE was not fitted on. Shuffled-label floor for this "
                                    f"probe size: race TVD {r['race_floor']:.3f}, gender TVD {r['gender_floor']:.3f}.\n")
        details.append(f"\n### {name}\nmost over-represented nodes per race group (ratio to pooled):\n" +
                       "\n".join(f"- {g}: " + ", ".join(f"{s} x{ratio:.1f}" for s, ratio in v[:5]) for g, v in r["over"].items()) +
                       "\n\nnodes loading most on race directions: " + ", ".join(f"{s} {v:.2f}" for s, v in r["loading"]))
    (DATA / f"fairness_report{f'_{tag}' if tag else ''}.md").write_text("\n".join(([floor_line] if floor_line else []) + lines + details) + "\n")
    print(f"wrote data/fairness_report{f'_{tag}' if tag else ''}.md")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="config names to run")
    ap.add_argument("--tag", default="", help="use index_TAG.npz / image_vecs_TAG.npz for the unmasked rows")
    a = ap.parse_args()
    main(a.only, a.tag)
