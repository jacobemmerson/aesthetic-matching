"""Bias metrics over probe embeddings: label parity across groups, attribute recoverability,
and how much each node centroid points along an attribute direction."""
import numpy as np

from pipeline.build_index import normalize
from pipeline.logreg import cv_accuracy

OVER_TOP = 10


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
