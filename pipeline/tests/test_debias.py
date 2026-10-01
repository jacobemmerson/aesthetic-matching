import numpy as np

from pipeline.debias import apply, leace_fit, onehot, projection_from_basis, prompt_directions


def test_leace_equalises_class_means_and_rank():
    rng = np.random.default_rng(0)
    race, gender = rng.integers(0, 3, 300), rng.integers(0, 2, 300)
    X = rng.normal(size=(300, 10)).astype(np.float32)
    X[:, 0] += race; X[:, 1] += 2 * gender; X[:, 2] += race * gender
    Z = np.concatenate([onehot(race, 3), onehot(gender, 2)], 1)
    P, b = leace_fit(X, Z)
    Y = apply(X, P, b)
    for col in range(Z.shape[1]):
        np.testing.assert_allclose(Y[Z[:, col] == 1].mean(0), Y.mean(0), atol=1e-3)
    assert np.linalg.matrix_rank(P, tol=1e-4) == 10 - (3 - 1) - (2 - 1)
    assert Y.shape == X.shape and Y.dtype == np.float32


def test_projection_from_basis_removes_direction():
    basis = np.array([[1, 0, 0]], np.float32)
    P, b = projection_from_basis(basis)
    out = apply(np.array([[3, 1, 2]], np.float32), P, b)
    np.testing.assert_allclose(out, [[0, 1, 2]], atol=1e-6)


def test_prompt_directions_are_orthonormal():
    def fake_embed(texts):  # deterministic per text within one process
        return np.stack([np.random.default_rng(abs(hash(t)) % 2**32).normal(size=16) for t in texts]).astype(np.float32)
    dirs = prompt_directions(fake_embed)
    assert dirs.shape == (6 + 1, 16)  # 7 race groups -> 6, 2 genders -> 1
    np.testing.assert_allclose(dirs @ dirs.T, np.eye(7), atol=1e-5)
