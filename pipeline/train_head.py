"""Linear head over frozen CLIP vectors: multinomial logistic regression with optional
per-row weights that balance race/gender mix within each node."""
import numpy as np

from pipeline.logreg import fit, folds, logits

WEIGHT_CLIP = (0.2, 5.0)


def group_weights(groups: np.ndarray, owner_idx: np.ndarray, none_value: int = -1) -> np.ndarray:
    """global_share(group) / node_share(group) per row, so each node's effective group mix matches
    the dataset's. Rows without a face (none) keep weight 1."""
    has = groups != none_value
    w = np.ones(len(groups), np.float32)
    glob = {g: (groups[has] == g).mean() for g in np.unique(groups[has])}
    for node in np.unique(owner_idx):
        rows = (owner_idx == node) & has
        for g in np.unique(groups[rows]):
            share = (groups[rows] == g).mean()
            w[rows & (groups == g)] = np.clip(glob[g] / share, *WEIGHT_CLIP)
    return w


def train(X, owner_idx, n_classes, weights=None, l2=1e-3):
    return fit(X, owner_idx, n_classes, l2, weights)


def cv_scores(X, owner_idx, n_classes, source, weights=None, l2=1e-3, k=5) -> np.ndarray:
    f = folds(len(X), k, groups=source)
    out = np.zeros((len(X), n_classes), np.float32)
    for i in range(k):
        tr = f != i
        W, b = fit(X[tr], owner_idx[tr], n_classes, l2, None if weights is None else weights[tr])
        out[~tr] = logits(X[~tr], W, b)
    return out


def zscore(scores: np.ndarray) -> np.ndarray:
    return (scores - scores.mean(1, keepdims=True)) / np.maximum(scores.std(1, keepdims=True), 1e-6)
