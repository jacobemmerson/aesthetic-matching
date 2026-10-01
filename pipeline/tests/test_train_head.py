import numpy as np

from pipeline.train_head import cv_scores, group_weights, train, zscore


def test_group_weights_balance_each_node_to_global_mix():
    owner = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    groups = np.array([0, 0, 0, 1, 0, 1, 1, -1])  # node 0 is 3:1 group 0; global (faces) is 4:3
    w = group_weights(groups, owner)
    assert w[7] == 1.0  # none
    assert w[3] > w[0]  # minority-in-node rows upweighted
    assert 0.2 <= w.min() and w.max() <= 5


def test_cv_scores_keep_crops_in_one_fold():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 6)).astype(np.float32)
    owner = np.repeat([0, 1], 20); X[:, 0] += 5 * owner
    source = np.repeat(np.arange(20), 2)  # pairs of crops
    s = cv_scores(X, owner, 2, source)
    assert s.shape == (40, 2) and (s.argmax(1) == owner).mean() > 0.9


def test_train_and_zscore():
    X = np.array([[1, 0], [0, 1]], np.float32)
    W, b = train(np.repeat(X, 10, 0), np.repeat([0, 1], 10), 2)
    z = zscore(X @ W.T + b)
    np.testing.assert_allclose(z.mean(1), 0, atol=1e-6)
    assert z[0, 0] > 0 > z[0, 1]
