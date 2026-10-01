"""Bias metrics over probe embeddings: label parity across groups, attribute recoverability,
and how much each node centroid points along an attribute direction."""
import argparse
from pathlib import Path

import numpy as np

from pipeline.build_index import MIN_IMAGES, normalize
from pipeline.debias import RACE_GROUPS, apply
from pipeline.evaluate import accuracy, loo_sims
from pipeline.logreg import cv_accuracy
from pipeline.train_head import cv_scores, group_weights, train, zscore
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


def load_bundle(masked: bool):
    suffix = "_masked" if masked else ""
    paths = [DATA / f"{n}{suffix}.npz" for n in ("index", "image_vecs", "probe")]
    if not all(p.exists() for p in paths):
        return None
    return tuple(np.load(p) for p in paths)


def treatment_map(name: str, masked: bool, d: int):
    if name == "none":
        return np.eye(d, dtype=np.float32), np.zeros(d, np.float32)
    suffix = "_masked" if masked and name == "leace" else ""
    t = np.load(DATA / f"debias_{name}{suffix}.npz")
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
    vecs, pvecs, text = apply(img["vecs"], P, b), apply(probe["vecs"], P, b), apply(z["text_vecs"], P, b)
    counts, prior = z["counts"], z["prior"]
    mean_img, mean_txt = apply(z["mean_img"][None], P, b)[0], apply(z["mean_txt"][None], P, b)[0]
    txt_ref = normalize(vecs - mean_txt) @ normalize(text - mean_txt).T
    txt_probe = normalize(pvecs - mean_txt) @ normalize(text - mean_txt).T
    sums = np.zeros_like(z["centroids"]); np.add.at(sums, owner_idx, vecs)
    if scorer == "centroid":
        cents = normalize(sums)
        ref = loo_sims(vecs, owner_idx, len(slugs), mean_img)
        pro = normalize(pvecs - mean_img) @ normalize(cents - mean_img).T
        ref_s = np.where(counts > 0, IMAGE_WEIGHT * ref + TEXT_WEIGHT * txt_ref, txt_ref) + PRIOR_WEIGHT * prior
        pro_s = np.where(counts > 0, IMAGE_WEIGHT * pro + TEXT_WEIGHT * txt_probe, txt_probe) + PRIOR_WEIGHT * prior
    else:
        w = group_weights(attrs["race"][img["source"]], owner_idx) if scorer == "head_rw" else None
        ref_s = zscore(cv_scores(vecs, owner_idx, len(slugs), img["source"], w))
        W, hb = train(vecs, owner_idx, len(slugs), w)
        pro_s = zscore(pvecs @ W.T + hb)
        fallback = counts < MIN_IMAGES
        ref_s = np.where(fallback, zscore(txt_ref), ref_s) + PRIOR_WEIGHT * prior
        pro_s = np.where(fallback, zscore(txt_probe), pro_s) + PRIOR_WEIGHT * prior
    plain_w = 1 / counts[owner_idx]
    top1 = pro_s.argmax(1)
    race_par, gender_par = parity(top1, probe["race"], len(slugs)), parity(top1, probe["gender"], len(slugs))
    loading = node_loading(sums, group_directions(pvecs, probe["race"]))
    return {"race_tvd": race_par["max_tvd"], "gender_tvd": gender_par["max_tvd"],
            "race_acc": recoverability(pvecs, probe["race"])["acc"], "gender_acc": recoverability(pvecs, probe["gender"])["acc"],
            "top1": accuracy(ref_s, owner_idx, plain_w, 1), "top5": accuracy(ref_s, owner_idx, plain_w, 5),
            "over": {RACE_GROUPS[g]: [(slugs[i], r) for i, r in v] for g, v in race_par["over"].items()},
            "loading": [(slugs[i], float(np.abs(loading[i]).max())) for i in np.argsort(-np.abs(loading).max(1))[:OVER_TOP]]}


def main(only: list[str] | None):
    attrs = np.load(DATA / "reference_attrs.npz")
    lines = ["| config | race TVD | gender TVD | race acc (chance 0.143) | gender acc (chance 0.5) | LOO top1 | LOO top5 |",
             "|---|---|---|---|---|---|---|"]
    if attrs["race_cv_acc"] < 0.6 or attrs["gender_cv_acc"] < 0.85:
        lines.insert(0, f"WARNING: attribute labels are noisy (race {attrs['race_cv_acc']:.2f}, gender {attrs['gender_cv_acc']:.2f}); "
                        "reweighted rows are unreliable\n")
    details = []
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
        details.append(f"\n### {name}\nmost over-represented nodes per race group (ratio to pooled):\n" +
                       "\n".join(f"- {g}: " + ", ".join(f"{s} x{ratio:.1f}" for s, ratio in v[:5]) for g, v in r["over"].items()) +
                       "\n\nnodes loading most on race directions: " + ", ".join(f"{s} {v:.2f}" for s, v in r["loading"]))
    (DATA / "fairness_report.md").write_text("\n".join(lines + details) + "\n")
    print("wrote data/fairness_report.md")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="config names to run")
    main(ap.parse_args().only)
