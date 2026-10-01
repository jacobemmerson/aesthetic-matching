"""Affine maps that remove race and gender information from CLIP vectors. Both methods return
(P, b) applied as vecs @ P.T + b, so the index stores one matrix whichever method wins."""
import argparse
from pathlib import Path
from typing import Callable

import numpy as np

DATA = Path(__file__).resolve().parent.parent / "data"
RACE_GROUPS = ["East Asian", "Indian", "Black", "White", "Middle Eastern", "Latino Hispanic", "Southeast Asian"]
GENDER_GROUPS = ["man", "woman"]
TEMPLATES = ["a photo of a {} person", "a portrait of a {} person", "a picture of a {} face", "a {} person"]
GENDER_TEMPLATES = ["a photo of a {}", "a portrait of a {}", "a picture of a {}", "a {}"]


def fit_rows(n: int) -> np.ndarray:
    """Probe rows LEACE is fitted on (even rows); fairness.py measures on the rest."""
    return np.arange(n) % 2 == 0


def onehot(labels: np.ndarray, k: int) -> np.ndarray:
    return np.eye(k, dtype=np.float32)[np.asarray(labels)]


def apply(vecs: np.ndarray, P: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (vecs @ P.T + b).astype(np.float32)


def projection_from_basis(basis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    q, _ = np.linalg.qr(basis.T)
    P = np.eye(basis.shape[1], dtype=np.float32) - (q @ q.T).astype(np.float32)
    return P, np.zeros(basis.shape[1], np.float32)


def _group_basis(embed_texts: Callable, groups: list[str], templates: list[str]) -> np.ndarray:
    means = np.stack([embed_texts([t.format(g) for t in templates]).mean(0) for g in groups])
    diffs = means[1:] - means[0]
    q, _ = np.linalg.qr(diffs.T)
    return q.T


def prompt_directions(embed_texts: Callable[[list[str]], np.ndarray]) -> np.ndarray:
    """Chuang et al. 2023: attribute subspace from paired prompts, no labels needed."""
    race = _group_basis(embed_texts, RACE_GROUPS, TEMPLATES)
    gender = _group_basis(embed_texts, GENDER_GROUPS, GENDER_TEMPLATES)
    q, _ = np.linalg.qr(np.concatenate([race, gender]).T)
    return q.T.astype(np.float32)


def leace_fit(X: np.ndarray, Z: np.ndarray, ridge: float = 1e-4) -> tuple[np.ndarray, np.ndarray]:
    """Belrose et al. 2023 closed form: whiten, project out the span of the whitened cross
    covariance with the labels, unwhiten. Afterwards every label column has the same mean."""
    X, Z = X.astype(np.float64), Z.astype(np.float64)
    mu = X.mean(0)
    Xc, Zc = X - mu, Z - Z.mean(0)
    sxx = Xc.T @ Xc / len(X) + ridge * np.eye(X.shape[1])
    sxz = Xc.T @ Zc / len(X)
    evals, evecs = np.linalg.eigh(sxx)
    W = evecs @ np.diag(evals**-0.5) @ evecs.T
    W_inv = evecs @ np.diag(evals**0.5) @ evecs.T
    U, s, _ = np.linalg.svd(W @ sxz, full_matrices=False)
    U = U[:, s > 1e-6 * s.max()]
    P = np.eye(X.shape[1]) - W_inv @ U @ U.T @ W
    return P.astype(np.float32), (mu - P @ mu).astype(np.float32)


def main():
    from pipeline.build_index import embed_texts

    P, b = projection_from_basis(prompt_directions(embed_texts))
    np.savez(DATA / "debias_prompt.npz", P=P, b=b)
    print("wrote data/debias_prompt.npz")
    for suffix in ("", "_masked"):
        probe = DATA / f"probe{suffix}.npz"
        if not probe.exists():
            continue
        z = np.load(probe)
        rows = fit_rows(len(z["race"]))
        Z = np.concatenate([onehot(z["race"][rows], len(RACE_GROUPS)), onehot(z["gender"][rows], len(GENDER_GROUPS))], 1)
        P, b = leace_fit(z["vecs"][rows], Z)
        np.savez(DATA / f"debias_leace{suffix}.npz", P=P, b=b)
        print(f"wrote data/debias_leace{suffix}.npz: rank {np.linalg.matrix_rank(P, tol=1e-4)} of {P.shape[0]}")


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    main()
