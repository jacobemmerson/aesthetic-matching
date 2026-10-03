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


def test_centroid_probe_scores_match_server_index():
    from pipeline.fairness import centroid_probe_scores
    from server.match import Index

    rng = np.random.default_rng(0)
    raw = rng.normal(size=(12, 6)).astype(np.float32)
    owner_idx = np.repeat([0, 1, 2], 4)
    sums = np.zeros((3, 6), np.float32); np.add.at(sums, owner_idx, raw)
    P = np.linalg.qr(rng.normal(size=(6, 6)))[0].astype(np.float32) * 0.7  # non-orthonormal map with a shift
    b = rng.normal(size=6).astype(np.float32)
    z = {"centroids": sums / np.linalg.norm(sums, axis=1, keepdims=True), "text_vecs": rng.normal(size=(3, 6)).astype(np.float32),
         "counts": np.array([4, 4, 4]), "prior": np.array([0.1, 0.5, 0.9], np.float32)}
    z["mean_img"], z["mean_txt"] = z["centroids"].mean(0), z["text_vecs"].mean(0)
    idx = Index(["a", "b", "c"], z["centroids"], z["text_vecs"], z["counts"], np.zeros((3, 2)), z["mean_img"], z["mean_txt"], z["prior"],
                proj_P=P, proj_b=b)
    probe = rng.normal(size=(5, 6)).astype(np.float32)
    got = centroid_probe_scores(probe, sums, z, P, b)
    np.testing.assert_allclose(got, np.stack([idx.scores(q) for q in probe]), atol=1e-5)


def test_parity_floor_is_small_for_random_labels():
    from pipeline.fairness import parity_floor

    rng = np.random.default_rng(0)
    top1 = rng.integers(0, 50, 2000)
    groups = rng.integers(0, 7, 2000)
    assert 0 < parity_floor(top1, groups, 50) < 0.3


def test_align_by_path_maps_labels_onto_another_build_of_the_same_images():
    from pipeline.fairness import align_by_path

    labels = np.array([2, 0, 1])
    out = align_by_path(labels, ["a.jpg", "b.jpg", "c.jpg"], ["c.jpg", "zzz.jpg", "a.jpg", "a.jpg"])
    assert out.tolist() == [1, -1, 2, 2]  # unknown paths get -1 (no group)
