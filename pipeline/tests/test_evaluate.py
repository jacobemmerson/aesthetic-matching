import numpy as np

from pipeline.build_index import normalize
from pipeline.evaluate import accuracy, loo_scores


def test_loo_removes_self_from_own_centroid():
    # node 0 has two images pointing different ways; node 1 has one. Without LOO every image would
    # trivially match its own centroid; with LOO, image 0's centroid becomes image 1 (orthogonal).
    vecs = normalize(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32))
    owner = np.array([0, 0, 1])
    sums = np.zeros((2, 3), np.float32); np.add.at(sums, owner, vecs)
    sims = loo_scores(vecs, owner, sums, np.array([2, 1]), np.zeros(3, np.float32))
    assert abs(sims[0, 0]) < 1e-6 and abs(sims[1, 0]) < 1e-6  # own class now orthogonal
    assert sims[2, 1] == -1  # singleton excluded
    assert abs(sims[0, 1]) < 1e-6


def test_accuracy_weighted():
    scores = np.array([[0.9, 0.1], [0.2, 0.8], [0.7, 0.3]])
    owner = np.array([0, 1, 1])
    assert accuracy(scores, owner, np.ones(3), 1) == 2 / 3
    assert accuracy(scores, owner, np.array([1, 1, 0]), 1) == 1.0
    assert accuracy(scores, owner, np.ones(3), 2) == 1.0


def test_loo_keeps_coherent_class_on_top_with_centering():
    rng = np.random.default_rng(0)
    base = normalize(rng.normal(size=(2, 16)).astype(np.float32))
    vecs = normalize(np.concatenate([base[0] + 0.3 * rng.normal(size=(6, 16)), base[1] + 0.3 * rng.normal(size=(6, 16))]).astype(np.float32))
    owner = np.array([0] * 6 + [1] * 6)
    sums = np.zeros((2, 16), np.float32); np.add.at(sums, owner, vecs)
    mean = normalize(sums).mean(0)
    sims = loo_scores(vecs, owner, sums, np.array([6, 6]), mean)
    assert (sims.argmax(1) == owner).all()


def test_loo_sims_wraps_loo_scores():
    from pipeline.evaluate import loo_sims

    vecs = normalize(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32))
    sims = loo_sims(vecs, np.array([0, 0, 1]), 2, np.zeros(3, np.float32))
    assert sims.shape == (3, 2) and sims[2, 1] == -1
