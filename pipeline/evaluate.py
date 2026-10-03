"""Leave-one-out matching accuracy on the reference images, over a grid of blend weight and
popularity-prior strength. Each image is scored against centroids with itself removed.

Two numbers per setting: plain accuracy (every aesthetic counts equally) and popularity-weighted
accuracy (an aesthetic's images count in proportion to its prior), the latter being closer to what
real users upload. A prior can only help the weighted number; check it doesn't wreck the plain one.
"""
import argparse
import itertools
from pathlib import Path

import numpy as np

from pipeline.build_index import normalize

DATA = Path(__file__).resolve().parent.parent / "data"


def loo_scores(vecs, owner_idx, sums, counts, mean_img, project=lambda v: v):
    """Cosine of each image against every centroid; its own centroid is rebuilt without it.
    `sums` is the per-node sum of unit image vectors (not the normalized centroid). `project` is
    the index's debias map, applied after unit-normalizing exactly as server/match.Index does;
    `mean_img` is already projected."""
    cents = project(normalize(sums))
    q = normalize(project(vecs) - mean_img)
    sims = q @ normalize(cents - mean_img).T
    for i, o in enumerate(owner_idx):
        if counts[o] > 1:
            loo = normalize(project(normalize(sums[o] - vecs[i])) - mean_img)  # unit centroid, project, center: like the others
            sims[i, o] = q[i] @ loo
        else:
            sims[i, o] = -1  # singleton: no fair score
    return sims


def loo_sims(vecs, owner_idx, n_nodes, mean_img, project=lambda v: v):
    sums = np.zeros((n_nodes, vecs.shape[1]), np.float32)
    np.add.at(sums, owner_idx, vecs)
    return loo_scores(vecs, owner_idx, sums, np.bincount(owner_idx, minlength=n_nodes), mean_img, project)


def accuracy(scores: np.ndarray, owner_idx: np.ndarray, weights: np.ndarray, k: int) -> float:
    topk = np.argsort(-scores, axis=1)[:, :k]
    hit = (topk == owner_idx[:, None]).any(1)
    return float((hit * weights).sum() / weights.sum())


def main(alphas, image_weights, tag: str = ""):
    suffix = f"_{tag}" if tag else ""
    z, img = np.load(DATA / f"index{suffix}.npz"), np.load(DATA / f"image_vecs{suffix}.npz")
    slugs = list(z["slugs"])
    owner_idx = np.array([slugs.index(o) for o in img["owner"]])
    vecs, counts = img["vecs"], z["counts"]
    img_sims = loo_sims(vecs, owner_idx, len(slugs), z["mean_img"])
    txt_sims = normalize(vecs - z["mean_txt"]) @ normalize(z["text_vecs"] - z["mean_txt"]).T
    prior = z["prior"]
    plain_w = 1 / counts[owner_idx]  # each aesthetic contributes 1 in total
    pop_w = plain_w * (0.05 + prior[owner_idx])  # plus proportional to how known it is
    print(f"{len(vecs)} images, {len(slugs)} aesthetics, singletons excluded from their own class: {(counts[owner_idx] == 1).sum()}")
    print(f"{'img_w':>6} {'alpha':>6} | {'top1':>6} {'top5':>6} | {'top1 pop-weighted':>18} {'top5':>6}")
    for w, a in itertools.product(image_weights, alphas):
        s = w * img_sims + (1 - w) * txt_sims + a * prior[None, :]
        print(f"{w:6.2f} {a:6.3f} | {accuracy(s, owner_idx, plain_w, 1):6.3f} {accuracy(s, owner_idx, plain_w, 5):6.3f} | "
              f"{accuracy(s, owner_idx, pop_w, 1):18.3f} {accuracy(s, owner_idx, pop_w, 5):6.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--alphas", type=float, nargs="+", default=[0, 0.01, 0.02, 0.03, 0.05, 0.08])
    ap.add_argument("--image-weights", type=float, nargs="+", default=[0.5, 0.7, 0.85, 1.0])
    ap.add_argument("--tag", default="", help="evaluate index_TAG.npz / image_vecs_TAG.npz")
    a = ap.parse_args()
    main(a.alphas, a.image_weights, a.tag)
