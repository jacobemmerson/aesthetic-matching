"""Multinomial logistic regression in torch (LBFGS, CPU). Shared by the probe labeler, the
recoverability metric and the linear head so there is one implementation to trust."""
import numpy as np


def fit(X: np.ndarray, y: np.ndarray, n_classes: int, l2: float = 1e-3, weights: np.ndarray | None = None,
        seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    import torch

    torch.manual_seed(seed)
    Xt, yt = torch.as_tensor(X, dtype=torch.float32), torch.as_tensor(y, dtype=torch.long)
    wt = torch.ones(len(y)) if weights is None else torch.as_tensor(weights, dtype=torch.float32)
    wt = wt / wt.sum()
    W = torch.zeros(n_classes, X.shape[1], requires_grad=True)
    b = torch.zeros(n_classes, requires_grad=True)
    opt = torch.optim.LBFGS([W, b], max_iter=200, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        loss = (torch.nn.functional.cross_entropy(Xt @ W.T + b, yt, reduction="none") * wt).sum() + l2 * (W**2).sum()
        loss.backward()
        return loss

    opt.step(closure)
    return W.detach().numpy(), b.detach().numpy()


def logits(X: np.ndarray, W: np.ndarray, b: np.ndarray) -> np.ndarray:
    return X @ W.T + b


def folds(n: int, k: int, groups: np.ndarray | None = None, seed: int = 0) -> np.ndarray:
    """Fold id per row. Rows with the same group id (e.g. crops of one image) share a fold."""
    rng = np.random.default_rng(seed)
    groups = np.arange(n) if groups is None else np.asarray(groups)
    uniq = np.unique(groups)
    fold_of_group = dict(zip(uniq, rng.permutation(len(uniq)) % k))
    return np.array([fold_of_group[g] for g in groups])


def cv_accuracy(X: np.ndarray, y: np.ndarray, n_classes: int, k: int = 5, l2: float = 1e-3,
                groups: np.ndarray | None = None) -> float:
    f = folds(len(y), k, groups)
    hits = 0
    for i in range(k):
        W, b = fit(X[f != i], y[f != i], n_classes, l2)
        hits += int((logits(X[f == i], W, b).argmax(1) == y[f == i]).sum())
    return hits / len(y)
