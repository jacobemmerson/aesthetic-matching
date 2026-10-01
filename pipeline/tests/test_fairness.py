import numpy as np

from pipeline.fairness import group_directions, node_loading, parity, recoverability


def test_parity_zero_when_identical_and_one_when_disjoint():
    same = parity(np.array([0, 1, 0, 1]), np.array([0, 0, 1, 1]), 2)
    assert same["max_tvd"] == 0.0
    disjoint = parity(np.array([0, 0, 1, 1]), np.array([0, 0, 1, 1]), 2)
    assert disjoint["max_tvd"] == 1.0
    assert disjoint["over"][1][0][0] == 1  # node 1 is the over-represented one for group 1


def test_recoverability_drops_after_removing_axis():
    rng = np.random.default_rng(0)
    labels = rng.integers(0, 2, 200)
    vecs = rng.normal(size=(200, 8)).astype(np.float32)
    vecs[:, 0] += 4 * labels
    assert recoverability(vecs, labels)["acc"] > 0.95
    vecs[:, 0] = 0
    r = recoverability(vecs, labels)
    assert abs(r["acc"] - r["chance"]) < 0.15


def test_group_directions_and_loading():
    vecs = np.array([[1, 0, 0], [1, 0.1, 0], [0, 1, 0], [0, 1, 0.1]], np.float32)
    dirs = group_directions(vecs, np.array([0, 0, 1, 1]))
    assert dirs.shape == (1, 3)
    load = node_loading(np.array([[1, 0, 0], [0, 0, 1]], np.float32), dirs)
    assert abs(load[0, 0]) > 0.6 and abs(load[1, 0]) < 0.1
