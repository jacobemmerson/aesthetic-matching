import numpy as np

from pipeline.logreg import cv_accuracy, fit, folds, logits


def blobs(seed=0, n=60):
    rng = np.random.default_rng(seed)
    X = np.concatenate([rng.normal(c, 0.3, (n, 4)) for c in ([2, 0, 0, 0], [0, 2, 0, 0], [0, 0, 2, 0])]).astype(np.float32)
    return X, np.repeat([0, 1, 2], n)


def test_fit_separates_blobs():
    X, y = blobs()
    W, b = fit(X, y, 3)
    assert W.shape == (3, 4) and b.shape == (3,)
    assert (logits(X, W, b).argmax(1) == y).mean() > 0.98


def test_weights_shift_decision():
    X, y = blobs()
    heavy = np.where(y == 0, 50.0, 1.0)
    _, b0 = fit(X, y, 3)
    _, b1 = fit(X, y, 3, weights=heavy)
    assert b1[0] - b0[0] > 0  # class 0 bias rises when its rows are upweighted


def test_folds_keep_groups_together():
    groups = np.repeat(np.arange(10), 3)
    f = folds(30, 5, groups=groups)
    assert f.shape == (30,) and set(f) == set(range(5))
    for g in range(10):
        assert len(set(f[groups == g])) == 1


def test_cv_accuracy_high_on_blobs():
    X, y = blobs()
    assert cv_accuracy(X, y, 3) > 0.95
