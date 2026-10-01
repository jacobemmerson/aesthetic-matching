# Bias Mitigation and Linear Head Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure race and gender bias in the CLIP aesthetic matcher, compare four mitigations plus a linear head in one report, and wire the winner into the served index.

**Architecture:** Everything is numpy over frozen CLIP embeddings. A probe set (FairFace) gives labeled vectors; `fairness.py` scores every configuration (scorer x treatment) against the same metrics and writes one table. Treatments are affine maps `(P, b)` stored in `index.npz` so `server/match.py` only gains one matrix multiply and an optional face-mask call.

**Tech Stack:** Python 3.12, numpy 2.5, torch 2.14 CPU (logistic regression, no scikit-learn), open-clip ViT-B/32, `datasets` (FairFace download), `opencv-python-headless` (YuNet face detector), pytest, uv.

**Spec:** `docs/superpowers/specs/2026-09-30-bias-mitigation-design.md`

## Global Constraints

- No scikit-learn and no `concept-erasure`; logistic regression and LEACE are torch/numpy in-repo.
- Only two new dependencies: `datasets` (dev/pipeline) and `opencv-python-headless` (runtime).
- Accuracy floor: leave-one-out top-5 (plain) must stay >= 0.69 (current 0.72).
- Attributes: FairFace's seven race groups and two genders, erased jointly, parity reported as the worst group.
- `PRIOR_WEIGHT`, `IMAGE_WEIGHT`, `TEXT_WEIGHT` unchanged throughout; retuning is a later pass.
- Existing `index.npz` without new keys must load and score exactly as today.
- Test each stage before spend: every CLI gets a `--limit` smoke run before its full run.
- Git: the user allows only read-only git unless they approve commits. Commit steps below run only after that approval; otherwise leave the work staged and report.
- Run everything with `uv run` from the repo root.

## Review Focus

1. A probe cell (race x gender) with fewer than 20 images must abort `probe.py` with counts printed, never silently produce a lopsided probe. Test in Task 6.
2. A reference image with no detectable face must get attribute `none` and head weight 1, not be dropped and not be labeled by a classifier guessing on clothing. Test in Task 6 and Task 7.
3. An upload with no face must pass through masking unchanged, and a missing YuNet model file must fail at server startup, not on the first request. Test in Task 4 and Task 10.
4. Head logits and text-fallback scores must be on the same scale before the prior is added, or text-only nodes either never or always win. Test in Task 10.
5. Random crops of one reference image must land in the same CV fold, or head accuracy is inflated by near-duplicates. Test in Task 7.

---

## File structure

| file | responsibility |
|---|---|
| `pipeline/logreg.py` (new) | weighted multinomial logistic regression in torch, k-fold helper. Used by probe labeler, recoverability metric, and the head. |
| `pipeline/fairness.py` (new) | metric functions (parity, recoverability, node_loading) and the report CLI over all configurations. |
| `pipeline/debias.py` (new) | `prompt_directions`, `leace_fit`, `apply`; CLI writes `data/debias_prompt.npz`, `data/debias_leace.npz`. |
| `pipeline/faces.py` (new) | YuNet detector wrapper and `mask()`; model download. |
| `pipeline/probe.py` (new) | FairFace download/sample/embed to `data/probe.npz`; attribute labeler to `data/reference_attrs.npz`. |
| `pipeline/train_head.py` (new) | head training with reweighting and grouped CV, `cv_scores()` for the report. |
| `pipeline/build_index.py` (modify) | `path`/`source` arrays in `image_vecs.npz`, `--crops`, `--mask-faces`, `--tag`, `--debias`, `--head`. |
| `pipeline/evaluate.py` (modify) | expose `loo_sims()` taking arrays so `fairness.py` can reuse it. |
| `server/match.py` (modify) | projection, head scoring, masked encoder. |
| `pipeline/tests/test_{logreg,fairness,debias,faces,train_head}.py` (new), `test_build_index.py`, `server/tests/test_server.py` (modify) | tests. |

---

### Task 1: Dependencies and shared logistic regression

**Files:**
- Modify: `pyproject.toml`
- Create: `pipeline/logreg.py`, `pipeline/tests/test_logreg.py`

**Interfaces:**
- Produces: `fit(X: np.ndarray, y: np.ndarray, n_classes: int, l2: float = 1e-3, weights: np.ndarray | None = None, seed: int = 0) -> tuple[np.ndarray, np.ndarray]` returning `(W (k,d), b (k,))`; `logits(X, W, b) -> (n,k)`; `folds(n: int, k: int, groups: np.ndarray | None = None, seed: int = 0) -> np.ndarray` of fold ids (rows sharing a group id share a fold); `cv_accuracy(X, y, n_classes, k=5, l2=1e-3, groups=None) -> float`.

- [ ] **Step 1: Add dependencies**

```bash
uv add opencv-python-headless
uv add --group dev datasets
uv run python -c "import cv2, datasets; print(cv2.__version__)"
```

- [ ] **Step 2: Write the failing tests**

```python
# pipeline/tests/test_logreg.py
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
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest pipeline/tests/test_logreg.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pipeline.logreg'`

- [ ] **Step 4: Implement**

```python
# pipeline/logreg.py
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
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest pipeline/tests/test_logreg.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit (if approved)**

```bash
git add pyproject.toml uv.lock pipeline/logreg.py pipeline/tests/test_logreg.py
git commit -m "feat(pipeline): add torch logistic regression helper"
```

---

### Task 2: Fairness metrics

**Files:**
- Create: `pipeline/fairness.py` (metrics only; CLI added in Task 8), `pipeline/tests/test_fairness.py`

**Interfaces:**
- Consumes: `pipeline.logreg.cv_accuracy`.
- Produces: `parity(top1: np.ndarray, groups: np.ndarray, n_nodes: int) -> dict` with keys `max_tvd: float`, `per_group: dict[group, np.ndarray dist]`, `over: dict[group, list[tuple[node_idx, ratio]]]` (10 most over-represented nodes vs pooled); `recoverability(vecs, labels) -> dict(acc, chance, majority)`; `node_loading(centroids: (m,d), directions: (r,d)) -> (m,r)` cosines; `group_directions(vecs, labels) -> (k-1, d)` orthonormal basis of group-mean differences.

- [ ] **Step 1: Write the failing tests**

```python
# pipeline/tests/test_fairness.py
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest pipeline/tests/test_fairness.py -v`
Expected: FAIL, module not found

- [ ] **Step 3: Implement**

```python
# pipeline/fairness.py
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
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest pipeline/tests/test_fairness.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit (if approved)**

```bash
git add pipeline/fairness.py pipeline/tests/test_fairness.py
git commit -m "feat(pipeline): add parity and recoverability metrics"
```

---

### Task 3: Debias maps (prompt projection and LEACE)

**Files:**
- Create: `pipeline/debias.py`, `pipeline/tests/test_debias.py`

**Interfaces:**
- Produces: `apply(vecs, P, b) -> vecs @ P.T + b`; `projection_from_basis(basis: (r,d)) -> (P, b)` with `b = 0`; `leace_fit(X: (n,d), Z: (n,k) one-hot, ridge=1e-4) -> (P, b)`; `prompt_directions(embed_texts: Callable[[list[str]], np.ndarray]) -> (r, d)` orthonormal basis built from `RACE_GROUPS`, `GENDER_GROUPS`, `TEMPLATES`; CLI `uv run python -m pipeline.debias` writes `data/debias_prompt.npz` and `data/debias_leace.npz` (keys `P`, `b`), plus `data/debias_leace_masked.npz` when `data/probe_masked.npz` exists.
- The one-hot for LEACE is `[race one-hot (7) | gender one-hot (2)]` built by `onehot(race, 7)` and `onehot(gender, 2)` concatenated; `onehot(labels, k)` is exported.

- [ ] **Step 1: Write the failing tests**

```python
# pipeline/tests/test_debias.py
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
    rng = np.random.default_rng(1)
    def fake_embed(texts):  # deterministic per text
        return np.stack([np.random.default_rng(abs(hash(t)) % 2**32).normal(size=16) for t in texts]).astype(np.float32)
    dirs = prompt_directions(fake_embed)
    assert dirs.shape == (6 + 1, 16)  # 7 race groups -> 6, 2 genders -> 1
    np.testing.assert_allclose(dirs @ dirs.T, np.eye(7), atol=1e-5)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest pipeline/tests/test_debias.py -v`
Expected: FAIL, module not found

- [ ] **Step 3: Implement**

```python
# pipeline/debias.py
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


def onehot(labels: np.ndarray, k: int) -> np.ndarray:
    return np.eye(k, dtype=np.float32)[np.asarray(labels)]


def apply(vecs: np.ndarray, P: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (vecs @ P.T + b).astype(np.float32)


def projection_from_basis(basis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    q, _ = np.linalg.qr(basis.T)
    P = np.eye(basis.shape[1], dtype=np.float32) - (q @ q.T).astype(np.float32)
    return P, np.zeros(basis.shape[1], np.float32)


def _group_basis(embed_texts: Callable, groups: list[str], noun_templates: list[str]) -> np.ndarray:
    means = np.stack([embed_texts([t.format(g) for t in noun_templates]).mean(0) for g in groups])
    diffs = means[1:] - means[0]
    q, _ = np.linalg.qr(diffs.T)
    return q.T


def prompt_directions(embed_texts: Callable[[list[str]], np.ndarray]) -> np.ndarray:
    """Chuang et al. 2023: attribute subspace from paired prompts, no labels needed."""
    race = _group_basis(embed_texts, RACE_GROUPS, TEMPLATES)
    gender = _group_basis(embed_texts, GENDER_GROUPS, ["a photo of a {}", "a portrait of a {}", "a picture of a {}", "a {}"])
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

    np.savez(DATA / "debias_prompt.npz", **dict(zip(("P", "b"), projection_from_basis(prompt_directions(embed_texts)))))
    for suffix in ("", "_masked"):
        probe = DATA / f"probe{suffix}.npz"
        if not probe.exists():
            continue
        z = np.load(probe)
        Z = np.concatenate([onehot(z["race"], len(RACE_GROUPS)), onehot(z["gender"], len(GENDER_GROUPS))], 1)
        P, b = leace_fit(z["vecs"], Z)
        np.savez(DATA / f"debias_leace{suffix}.npz", P=P, b=b)
        print(f"debias_leace{suffix}.npz: rank {np.linalg.matrix_rank(P, tol=1e-4)} of {P.shape[0]}")
    print("wrote data/debias_prompt.npz")


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    main()
```

Note for `test_prompt_directions_are_orthonormal`: `hash()` of a str is salted per process; that is fine because the fake only needs to be consistent within one run. The `rng` variable is unused; delete it.

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest pipeline/tests/test_debias.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit (if approved)**

```bash
git add pipeline/debias.py pipeline/tests/test_debias.py
git commit -m "feat(pipeline): add prompt projection and LEACE maps"
```

---

### Task 4: Face masking

**Files:**
- Create: `pipeline/faces.py`, `pipeline/tests/test_faces.py`

**Interfaces:**
- Produces: `mask(img: PIL.Image, boxes: list[tuple[int,int,int,int]], expand: float = 0.2) -> PIL.Image` (pure, boxes are `x, y, w, h`); `class Detector` with `__init__(model_path: Path = MODEL_PATH)` raising `FileNotFoundError` if absent, `boxes(img: PIL.Image) -> list[tuple]`, `mask(img) -> PIL.Image`; `download_model()`; constants `MODEL_PATH = DATA / "face_detection_yunet_2023mar.onnx"`, `MODEL_URL`.

- [ ] **Step 1: Write the failing tests**

```python
# pipeline/tests/test_faces.py
import numpy as np
import pytest
from PIL import Image

from pipeline.faces import Detector, mask


def test_mask_fills_expanded_box_with_mean_colour():
    img = Image.new("RGB", (100, 100), (0, 0, 0))
    img.paste((255, 255, 255), (40, 40, 60, 60))  # white 20x20 square at a known spot
    out = np.asarray(mask(img, [(40, 40, 20, 20)]))
    assert out[50, 50].tolist() != [255, 255, 255]  # no longer white
    assert out[36, 36].tolist() == out[50, 50].tolist()  # 20% expansion covered (40 - 4)
    assert out[10, 10].tolist() == [0, 0, 0]  # outside untouched


def test_mask_without_boxes_returns_same_pixels():
    img = Image.new("RGB", (8, 8), (10, 20, 30))
    assert np.array_equal(np.asarray(mask(img, [])), np.asarray(img))


def test_detector_requires_model_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        Detector(tmp_path / "missing.onnx")
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest pipeline/tests/test_faces.py -v`
Expected: FAIL, module not found

- [ ] **Step 3: Implement**

```python
# pipeline/faces.py
"""Face detection (OpenCV YuNet) and masking. Faces carry most of the race and gender signal
in a CLIP vector while aesthetics live in clothes and setting, so the index can be built and
queried with faces blanked out."""
from pathlib import Path

import numpy as np
from PIL import Image

DATA = Path(__file__).resolve().parent.parent / "data"
MODEL_PATH = DATA / "face_detection_yunet_2023mar.onnx"
MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SCORE_THRESHOLD = 0.6


def mask(img: Image.Image, boxes: list[tuple[int, int, int, int]], expand: float = 0.2) -> Image.Image:
    if not boxes:
        return img
    arr = np.array(img.convert("RGB"))
    fill = tuple(int(c) for c in arr.reshape(-1, 3).mean(0))
    out = img.copy()
    for x, y, w, h in boxes:
        dx, dy = int(w * expand), int(h * expand)
        out.paste(fill, (max(x - dx, 0), max(y - dy, 0), min(x + w + dx, img.width), min(y + h + dy, img.height)))
    return out


def download_model(path: Path = MODEL_PATH):
    import httpx

    path.write_bytes(httpx.get(MODEL_URL, follow_redirects=True, timeout=60).raise_for_status().content)


class Detector:
    def __init__(self, model_path: Path = MODEL_PATH):
        import cv2

        if not model_path.exists():
            raise FileNotFoundError(f"{model_path} missing; run `uv run python -m pipeline.faces` to download it")
        self._cv2 = cv2
        self._net = cv2.FaceDetectorYN.create(str(model_path), "", (320, 320), SCORE_THRESHOLD)

    def boxes(self, img: Image.Image) -> list[tuple[int, int, int, int]]:
        bgr = self._cv2.cvtColor(np.array(img.convert("RGB")), self._cv2.COLOR_RGB2BGR)
        self._net.setInputSize((bgr.shape[1], bgr.shape[0]))
        _, faces = self._net.detect(bgr)
        return [] if faces is None else [tuple(int(v) for v in f[:4]) for f in faces]

    def mask(self, img: Image.Image) -> Image.Image:
        return mask(img, self.boxes(img))


if __name__ == "__main__":
    download_model()
    print(f"wrote {MODEL_PATH}")
```

- [ ] **Step 4: Run to verify pass, then download the model and eyeball one real image**

Run: `uv run pytest pipeline/tests/test_faces.py -v`
Expected: 3 passed

```bash
uv run python -m pipeline.faces
uv run python -c "
from PIL import Image; from pathlib import Path; from pipeline.faces import Detector
p = next(Path('data/img').rglob('*.jpg')); d = Detector(); print(p, d.boxes(Image.open(p)))
d.mask(Image.open(p)).save('/home/taesur/.claude/jobs/899d80e5/tmp/masked.jpg')"
```
Open the saved file and confirm the face box is filled. If YuNet finds nothing on an obvious portrait, lower `SCORE_THRESHOLD` to 0.5 and retry.

- [ ] **Step 5: Commit (if approved)**

```bash
git add pipeline/faces.py pipeline/tests/test_faces.py
git commit -m "feat(pipeline): add YuNet face masking"
```
(`data/*.onnx` is data, not committed; add it to `.gitignore` if `data/` is not already ignored.)

---

### Task 5: Index build: paths, crops, masking, tags

**Files:**
- Modify: `pipeline/build_index.py` (`embed_images`, `main`, argparse), `pipeline/tests/test_build_index.py`

**Interfaces:**
- Produces: `embed_images(paths: list[Path], batch=32, crops: int = 0, masker=None, seed=0) -> tuple[np.ndarray vecs, np.ndarray source]` where `source[i]` is the index into `paths` the row came from (originals first, then crops in order); `random_crop(img: Image, rng) -> Image` (scale 0.5 to 0.9 of each side, random offset); `image_vecs{tag}.npz` gains `path` (str array, per row) and `source` (int array). `index{tag}.npz` gains `masked_faces` (bool scalar). Flags: `--crops K`, `--mask-faces`, `--tag NAME` (output suffix `_NAME`, graph.json written only when tag is empty). `--debias` and `--head` are added in Task 10.

- [ ] **Step 1: Write the failing tests**

```python
# append to pipeline/tests/test_build_index.py
from PIL import Image

from pipeline.build_index import random_crop


def test_random_crop_is_smaller_and_inside():
    img = Image.new("RGB", (100, 80))
    rng = np.random.default_rng(0)
    for _ in range(20):
        c = random_crop(img, rng)
        assert 50 <= c.width <= 90 and 40 <= c.height <= 72


def test_embed_images_source_rows(monkeypatch, tmp_path):
    from pipeline import build_index as bi

    class FakeModel:
        def encode_image(self, x):
            import torch
            return torch.ones(x.shape[0], 4)

    monkeypatch.setattr(bi, "load_model", lambda: (FakeModel(), lambda im: __import__("torch").zeros(3, 8, 8), None, __import__("torch")))
    paths = []
    for i in range(2):
        p = tmp_path / f"{i}.jpg"; Image.new("RGB", (32, 32)).save(p); paths.append(p)
    vecs, source = bi.embed_images(paths, crops=2)
    assert vecs.shape == (6, 4) and source.tolist() == [0, 1, 0, 0, 1, 1]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest pipeline/tests/test_build_index.py -v`
Expected: 2 new FAIL (import error on `random_crop`)

- [ ] **Step 3: Implement**

Replace `embed_images` and extend `main`/argparse in `pipeline/build_index.py`:

```python
def random_crop(img, rng) -> "Image.Image":
    fw, fh = rng.uniform(0.5, 0.9, 2)
    w, h = int(img.width * fw), int(img.height * fh)
    x, y = rng.integers(0, img.width - w + 1), rng.integers(0, img.height - h + 1)
    return img.crop((x, y, x + w, y + h))


def embed_images(paths: list[Path], batch: int = 32, crops: int = 0, masker=None, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Unit vectors for each path, then `crops` random crops per path. `source` maps every row
    back to its path index so crops stay with their image in CV folds and attribute labels."""
    from PIL import Image

    model, preprocess, _, torch = load_model()
    rng = np.random.default_rng(seed)

    def load(p):
        img = Image.open(p).convert("RGB")
        return masker.mask(img) if masker else img

    jobs = [(i, lambda p=p: load(p)) for i, p in enumerate(paths)]
    jobs += [(i, lambda p=p: random_crop(load(p), rng)) for _ in range(crops) for i, p in enumerate(paths)]
    out = []
    with torch.no_grad():
        for i in range(0, len(jobs), batch):
            imgs = torch.stack([preprocess(job()) for _, job in jobs[i : i + batch]])
            out.append(model.encode_image(imgs).float().numpy())
            print(f"  embedded {min(i + batch, len(jobs))}/{len(jobs)} images", end="\r")
    print()
    source = np.array([i for i, _ in jobs], dtype=np.int64)
    return (normalize(np.concatenate(out)) if out else np.zeros((0, 512), np.float32)), source
```

In `main(limit, crops=0, mask_faces=False, tag="")`:

```python
    masker = None
    if mask_faces:
        from pipeline.faces import Detector
        masker = Detector()
    image_vecs, source = embed_images(paths, crops=crops, masker=masker)
    owner = [owner[i] for i in source]
    ...
    suffix = f"_{tag}" if tag else ""
    np.savez(DATA / f"index{suffix}.npz", ..., masked_faces=np.array(mask_faces))
    np.savez(DATA / f"image_vecs{suffix}.npz", vecs=image_vecs, owner=np.array(owner),
             path=np.array([str(paths[i]) for i in source]), source=source)
    if not tag:
        (DATA / "graph.json").write_text(...)
```
argparse: `--crops` (int, default 0), `--mask-faces` (store_true), `--tag` (str, default ""). Centroids use all rows including crops (a crop is still an example of that aesthetic).

- [ ] **Step 4: Run tests and a smoke build**

Run: `uv run pytest pipeline/tests/test_build_index.py -v`
Expected: all pass

```bash
uv run python -m pipeline.build_index --limit 5 --crops 1 --mask-faces --tag smoke
uv run python -c "import numpy as np; z=np.load('data/image_vecs_smoke.npz'); print(z['vecs'].shape, z['source'][:5], z['path'][0])"
```
Expected: row count is twice the image count, `path` holds real paths. Delete `data/*_smoke.npz` afterwards.

- [ ] **Step 5: Commit (if approved)**

```bash
git add pipeline/build_index.py pipeline/tests/test_build_index.py
git commit -m "feat(pipeline): crops, face masking and tagged outputs in build_index"
```

---

### Task 6: Probe set and reference attribute labels

**Files:**
- Create: `pipeline/probe.py`, `pipeline/tests/test_probe.py`

**Interfaces:**
- Consumes: `pipeline.logreg.fit/logits/cv_accuracy`, `pipeline.faces.Detector`, `pipeline.build_index.embed_images`, `pipeline.debias.RACE_GROUPS/GENDER_GROUPS`.
- Produces: `data/probe.npz` (`vecs (n,512)`, `race (n,) int`, `gender (n,) int`, `id (n,) str`); `data/probe_masked.npz` with `--mask-faces`; `data/reference_attrs.npz` (`race`, `gender`, `race_conf`, `gender_conf`, aligned with `image_vecs.npz` rows; `race == -1` means `none`); `sample_cells(race, gender, per_cell, seed) -> np.ndarray indices` and `label_references(probe_vecs, race, gender, ref_vecs, has_face) -> dict` are pure and tested. Race ints follow `RACE_GROUPS` order, gender `GENDER_GROUPS` order (`man`=0, `woman`=1), mapped from FairFace's names via `FAIRFACE_RACE = {"East Asian": 0, "Indian": 1, "Black": 2, "White": 3, "Middle Eastern": 4, "Latino_Hispanic": 5, "Southeast Asian": 6}` and `FAIRFACE_GENDER = {"Male": 0, "Female": 1}`.
- CLI: `uv run python -m pipeline.probe [--limit N] [--per-cell 200] [--mask-faces]`. Aborts (exit 1, counts printed) if any cell has fewer than `MIN_CELL = 20` images.

- [ ] **Step 1: Write the failing tests**

```python
# pipeline/tests/test_probe.py
import numpy as np
import pytest

from pipeline.probe import label_references, sample_cells


def test_sample_cells_balanced_and_abort_on_thin_cell():
    race = np.repeat(np.arange(7), 60); gender = np.tile([0, 1], 210)
    idx = sample_cells(race, gender, per_cell=10, seed=0)
    assert len(idx) == 140
    for r in range(7):
        for g in range(2):
            assert ((race[idx] == r) & (gender[idx] == g)).sum() == 10
    thin = race.copy(); thin[(race == 6) & (gender == 1)] = 5  # empty one cell
    with pytest.raises(SystemExit):
        sample_cells(thin, gender, per_cell=10, seed=0)


def test_label_references_marks_faceless_as_none():
    rng = np.random.default_rng(0)
    race, gender = rng.integers(0, 7, 700), rng.integers(0, 2, 700)
    probe = rng.normal(size=(700, 8)).astype(np.float32)
    probe[:, 0] += 3 * race; probe[:, 1] += 3 * gender
    ref = probe[:10].copy()
    out = label_references(probe, race, gender, ref, has_face=np.array([True] * 9 + [False]))
    assert out["race"][:9].tolist() == race[:9].tolist() and out["gender"][:9].tolist() == gender[:9].tolist()
    assert out["race"][9] == -1 and out["gender"][9] == -1
    assert out["race_cv_acc"] > 0.9 and out["gender_cv_acc"] > 0.9
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest pipeline/tests/test_probe.py -v`
Expected: FAIL, module not found

- [ ] **Step 3: Implement**

```python
# pipeline/probe.py
"""FairFace probe set -> data/probe.npz, and race/gender labels for the reference images ->
data/reference_attrs.npz. Labels come from a logistic regression trained on the probe in the
same CLIP space, so no extra attribute model is needed; its held-out accuracy is stored so the
noise in the reference labels is known."""
import argparse
import sys
from pathlib import Path

import numpy as np

from pipeline.debias import GENDER_GROUPS, RACE_GROUPS
from pipeline.logreg import cv_accuracy, fit, logits

DATA = Path(__file__).resolve().parent.parent / "data"
FAIRFACE_RACE = {"East Asian": 0, "Indian": 1, "Black": 2, "White": 3, "Middle Eastern": 4, "Latino_Hispanic": 5, "Southeast Asian": 6}
FAIRFACE_GENDER = {"Male": 0, "Female": 1}
MIN_CELL = 20


def sample_cells(race: np.ndarray, gender: np.ndarray, per_cell: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    picked = []
    for r in range(len(RACE_GROUPS)):
        for g in range(len(GENDER_GROUPS)):
            cell = np.flatnonzero((race == r) & (gender == g))
            print(f"  {RACE_GROUPS[r]:>16} {GENDER_GROUPS[g]:>6}: {len(cell)} available")
            if len(cell) < MIN_CELL:
                sys.exit(f"cell {RACE_GROUPS[r]}/{GENDER_GROUPS[g]} has {len(cell)} < {MIN_CELL} images; probe would be lopsided")
            picked.append(rng.choice(cell, min(per_cell, len(cell)), replace=False))
    return np.concatenate(picked)


def label_references(probe_vecs, race, gender, ref_vecs, has_face) -> dict:
    out = {"race_cv_acc": cv_accuracy(probe_vecs, race, len(RACE_GROUPS)),
           "gender_cv_acc": cv_accuracy(probe_vecs, gender, len(GENDER_GROUPS))}
    for name, labels, k in (("race", race, len(RACE_GROUPS)), ("gender", gender, len(GENDER_GROUPS))):
        W, b = fit(probe_vecs, labels, k)
        z = logits(ref_vecs, W, b)
        p = np.exp(z - z.max(1, keepdims=True)); p /= p.sum(1, keepdims=True)
        out[name] = np.where(has_face, p.argmax(1), -1)
        out[f"{name}_conf"] = np.where(has_face, p.max(1), 0.0).astype(np.float32)
    return out


def load_fairface(limit: int | None):
    from datasets import load_dataset

    ds = load_dataset("HuggingFaceM4/FairFace", "0.25", split="validation")
    race_names, gender_names = ds.features["race"].names, ds.features["gender"].names
    race = np.array([FAIRFACE_RACE[race_names[r]] for r in ds["race"]])
    gender = np.array([FAIRFACE_GENDER[gender_names[g]] for g in ds["gender"]])
    return ds, race, gender


def main(limit, per_cell, mask_faces):
    from PIL import Image

    from pipeline.build_index import load_model, normalize
    from pipeline.faces import Detector

    ds, race, gender = load_fairface(limit)
    idx = sample_cells(race, gender, per_cell if limit is None else max(limit // 14, 1), seed=0)
    model, preprocess, _, torch = load_model()
    masker = Detector() if mask_faces else None
    vecs = []
    with torch.no_grad():
        for i in range(0, len(idx), 32):
            imgs = [ds[int(j)]["image"].convert("RGB") for j in idx[i : i + 32]]
            imgs = [masker.mask(im) if masker else im for im in imgs]
            vecs.append(model.encode_image(torch.stack([preprocess(im) for im in imgs])).float().numpy())
            print(f"  embedded {min(i + 32, len(idx))}/{len(idx)}", end="\r")
    print()
    suffix = "_masked" if mask_faces else ""
    np.savez(DATA / f"probe{suffix}.npz", vecs=normalize(np.concatenate(vecs)), race=race[idx], gender=gender[idx], id=idx.astype(str))
    print(f"wrote data/probe{suffix}.npz ({len(idx)} images)")
    if mask_faces:
        return  # reference labels come from the unmasked probe only
    ref = np.load(DATA / "image_vecs.npz")
    det = Detector()
    has_face = np.array([len(det.boxes(Image.open(p))) > 0 for p in ref["path"][:limit]])
    out = label_references(np.load(DATA / "probe.npz")["vecs"], race[idx], gender[idx], ref["vecs"][:limit], has_face)
    print(f"attribute classifier held-out acc: race {out['race_cv_acc']:.3f} gender {out['gender_cv_acc']:.3f}; "
          f"{int((~has_face).sum())}/{len(has_face)} reference images without a face")
    np.savez(DATA / "reference_attrs.npz", **out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="smoke run: ~N probe images and N reference rows")
    ap.add_argument("--per-cell", type=int, default=200)
    ap.add_argument("--mask-faces", action="store_true", help="write probe_masked.npz instead")
    a = ap.parse_args()
    main(a.limit, a.per_cell, a.mask_faces)
```

If `load_dataset` fails on the config name, run `uv run python -c "from datasets import get_dataset_config_names; print(get_dataset_config_names('HuggingFaceM4/FairFace'))"` and use the listed config. If the race label names differ from `FAIRFACE_RACE` keys, print `ds.features["race"].names` and fix the mapping; the seven groups are the same set.

- [ ] **Step 4: Run tests, then smoke, then full**

Run: `uv run pytest pipeline/tests/test_probe.py -v`
Expected: 2 passed

```bash
uv run python -m pipeline.probe --limit 50          # smoke: download + 14 cells x ~3
uv run python -m pipeline.probe                     # full: 2,800 images, a few minutes on CPU
uv run python -m pipeline.probe --mask-faces
uv run python -c "import numpy as np; z=np.load('data/reference_attrs.npz'); print(np.bincount(z['race']+1), z['race_cv_acc'], z['gender_cv_acc'])"
```
Expected: race held-out accuracy around 0.6 to 0.75 and gender above 0.9. Below 0.6 / 0.85 the report header warns (Task 8); note it but continue.

- [ ] **Step 5: Commit (if approved)**

```bash
git add pipeline/probe.py pipeline/tests/test_probe.py
git commit -m "feat(pipeline): FairFace probe set and reference attribute labels"
```

---

### Task 7: Linear head with reweighting and grouped CV

**Files:**
- Create: `pipeline/train_head.py`, `pipeline/tests/test_train_head.py`

**Interfaces:**
- Consumes: `pipeline.logreg.fit/logits/folds`.
- Produces: `group_weights(groups: np.ndarray, owner_idx: np.ndarray, none_value=-1) -> np.ndarray` (spec formula, clipped [0.2, 5], 1 for `none`); `cv_scores(X, owner_idx, n_classes, source, weights=None, l2=1e-3, k=5) -> np.ndarray (n, n_classes)` out-of-fold logits with crops grouped by `source`; `train(X, owner_idx, n_classes, weights=None, l2=1e-3) -> (W, b)`; `zscore(scores: (n,m)) -> (n,m)` per-row standardisation (used by the server too).

- [ ] **Step 1: Write the failing tests**

```python
# pipeline/tests/test_train_head.py
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
    owner = np.repeat([0, 1], 20); X[:, 0] += 3 * owner
    source = np.repeat(np.arange(20), 2)  # pairs of crops
    s = cv_scores(X, owner, 2, source)
    assert s.shape == (40, 2) and (s.argmax(1) == owner).mean() > 0.9


def test_train_and_zscore():
    X = np.array([[1, 0], [0, 1]], np.float32)
    W, b = train(np.repeat(X, 10, 0), np.repeat([0, 1], 10), 2)
    z = zscore(X @ W.T + b)
    np.testing.assert_allclose(z.mean(1), 0, atol=1e-6)
    assert z[0, 0] > 0 > z[0, 1]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest pipeline/tests/test_train_head.py -v`
Expected: FAIL, module not found

- [ ] **Step 3: Implement**

```python
# pipeline/train_head.py
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
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest pipeline/tests/test_train_head.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit (if approved)**

```bash
git add pipeline/train_head.py pipeline/tests/test_train_head.py
git commit -m "feat(pipeline): linear head with group reweighting"
```

---

### Task 8: Fairness report CLI and baseline

**Files:**
- Modify: `pipeline/fairness.py` (add `main`), `pipeline/evaluate.py` (factor out `loo_sims`), `pipeline/tests/test_evaluate.py`

**Interfaces:**
- Consumes: everything from Tasks 2, 3, 6, 7; `pipeline.evaluate.accuracy`.
- Produces: `evaluate.loo_sims(vecs, owner_idx, n_nodes, mean_img) -> (n, n_nodes)` (builds sums internally, wraps existing `loo_scores`); `fairness.CONFIGS: list[tuple[name, scorer, treatment, masked]]`; `fairness.run_config(...) -> dict` of the six numbers; CLI `uv run python -m pipeline.fairness [--only NAME ...]` prints the table and writes `data/fairness_report.md`.

- [ ] **Step 1: Write the failing test for `loo_sims`**

```python
# append to pipeline/tests/test_evaluate.py
from pipeline.evaluate import loo_sims


def test_loo_sims_wraps_loo_scores():
    vecs = normalize(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32))
    sims = loo_sims(vecs, np.array([0, 0, 1]), 2, np.zeros(3, np.float32))
    assert sims.shape == (3, 2) and sims[2, 1] == -1
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest pipeline/tests/test_evaluate.py -v`
Expected: 1 FAIL, import error

- [ ] **Step 3: Implement `loo_sims` and the report**

In `pipeline/evaluate.py`, after `loo_scores`:

```python
def loo_sims(vecs, owner_idx, n_nodes, mean_img):
    sums = np.zeros((n_nodes, vecs.shape[1]), np.float32)
    np.add.at(sums, owner_idx, vecs)
    return loo_scores(vecs, owner_idx, sums, np.bincount(owner_idx, minlength=n_nodes), mean_img)
```
and use it inside `main` in place of the three lines that build `sums` and call `loo_scores`.

Append to `pipeline/fairness.py`:

```python
import argparse
from pathlib import Path

from pipeline.debias import GENDER_GROUPS, RACE_GROUPS, apply
from pipeline.evaluate import accuracy, loo_sims
from pipeline.train_head import cv_scores, group_weights, train, zscore
from server.match import IMAGE_WEIGHT, PRIOR_WEIGHT, TEXT_WEIGHT

DATA = Path(__file__).resolve().parent.parent / "data"
MIN_IMAGES = 3
# name, scorer (centroid | head | head_rw), treatment (none | prompt | leace), masked
CONFIGS = [
    ("centroid", "centroid", "none", False),
    ("centroid+prompt", "centroid", "prompt", False),
    ("centroid+leace", "centroid", "leace", False),
    ("centroid+mask", "centroid", "none", True),
    ("centroid+mask+leace", "centroid", "leace", True),
    ("head", "head", "none", False),
    ("head_rw", "head_rw", "none", False),
    ("head_rw+leace", "head_rw", "leace", False),
    ("head_rw+mask+leace", "head_rw", "leace", True),
]


def load_bundle(masked: bool):
    suffix = "_masked" if masked else ""
    paths = [DATA / f"{n}{suffix}.npz" for n in ("index", "image_vecs", "probe")]
    if not all(p.exists() for p in paths):
        return None
    z, img, probe = (np.load(p) for p in paths)
    return z, img, probe


def treatment_map(name: str, masked: bool, d: int):
    if name == "none":
        return np.eye(d, dtype=np.float32), np.zeros(d, np.float32)
    suffix = "_masked" if masked and name == "leace" else ""
    t = np.load(DATA / f"debias_{name}{suffix}.npz")
    return t["P"], t["b"]


def run_config(scorer: str, treatment: str, masked: bool, attrs) -> dict | None:
    bundle = load_bundle(masked)
    if bundle is None:
        return None
    z, img, probe = bundle
    slugs = list(z["slugs"])
    owner_idx = np.array([slugs.index(o) for o in img["owner"]])
    P, b = treatment_map(treatment, masked, img["vecs"].shape[1])
    vecs, pvecs = apply(img["vecs"], P, b), apply(probe["vecs"], P, b)
    text = apply(z["text_vecs"], P, b)
    counts, prior = z["counts"], z["prior"]
    mean_img, mean_txt = apply(z["mean_img"][None], P, b)[0], apply(z["mean_txt"][None], P, b)[0]
    txt_ref = normalize(vecs - mean_txt) @ normalize(text - mean_txt).T
    txt_probe = normalize(pvecs - mean_txt) @ normalize(text - mean_txt).T
    if scorer == "centroid":
        cents = np.zeros_like(z["centroids"]); np.add.at(cents, owner_idx, vecs); cents = normalize(cents)
        ref = loo_sims(vecs, owner_idx, len(slugs), mean_img)
        pro = normalize(pvecs - mean_img) @ normalize(cents - mean_img).T
        ref_s = np.where(counts > 0, IMAGE_WEIGHT * ref + TEXT_WEIGHT * txt_ref, txt_ref) + PRIOR_WEIGHT * prior
        pro_s = np.where(counts > 0, IMAGE_WEIGHT * pro + TEXT_WEIGHT * txt_probe, txt_probe) + PRIOR_WEIGHT * prior
    else:
        w = group_weights(attrs["race"][img["source"]], owner_idx) if scorer == "head_rw" else None
        ref_s = zscore(cv_scores(vecs, owner_idx, len(slugs), img["source"], w))
        W, hb = train(vecs, owner_idx, len(slugs), w)
        pro_s = zscore(pvecs @ W.T + hb)
        fallback = counts < MIN_IMAGES
        ref_s = np.where(fallback, zscore(txt_ref), ref_s) + PRIOR_WEIGHT * prior
        pro_s = np.where(fallback, zscore(txt_probe), pro_s) + PRIOR_WEIGHT * prior
    sums = np.zeros_like(z["centroids"]); np.add.at(sums, owner_idx, vecs)
    plain_w = 1 / counts[owner_idx]
    top1 = pro_s.argmax(1)
    race_par, gender_par = parity(top1, probe["race"], len(slugs)), parity(top1, probe["gender"], len(slugs))
    return {"race_tvd": race_par["max_tvd"], "gender_tvd": gender_par["max_tvd"],
            "race_acc": recoverability(pvecs, probe["race"])["acc"], "gender_acc": recoverability(pvecs, probe["gender"])["acc"],
            "top1": accuracy(ref_s, owner_idx, plain_w, 1), "top5": accuracy(ref_s, owner_idx, plain_w, 5),
            "over": {RACE_GROUPS[g]: [(slugs[i], r) for i, r in v] for g, v in race_par["over"].items()},
            "loading": node_loading(sums, group_directions(pvecs, probe["race"]))}


def main(only: list[str] | None):
    attrs = np.load(DATA / "reference_attrs.npz")
    lines = ["| config | race TVD | gender TVD | race acc | gender acc | LOO top1 | LOO top5 |", "|---|---|---|---|---|---|---|"]
    if attrs["race_cv_acc"] < 0.6 or attrs["gender_cv_acc"] < 0.85:
        lines.insert(0, f"WARNING: attribute labels are noisy (race {attrs['race_cv_acc']:.2f}, gender {attrs['gender_cv_acc']:.2f}); reweighted rows are unreliable\n")
    details = []
    for name, scorer, treatment, masked in CONFIGS:
        if only and name not in only:
            continue
        r = run_config(scorer, treatment, masked, attrs)
        if r is None:
            lines.append(f"| {name} | (missing masked data) | | | | | |"); continue
        lines.append(f"| {name} | {r['race_tvd']:.3f} | {r['gender_tvd']:.3f} | {r['race_acc']:.3f} | {r['gender_acc']:.3f} | {r['top1']:.3f} | {r['top5']:.3f} |")
        details.append(f"\n### {name}: most over-represented nodes per race group\n" +
                       "\n".join(f"- {g}: " + ", ".join(f"{s} x{ratio:.1f}" for s, ratio in v[:5]) for g, v in r["over"].items()))
        print(lines[-1])
    (DATA / "fairness_report.md").write_text("\n".join(lines + details) + "\n")
    print("wrote data/fairness_report.md")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="config names to run")
    main(ap.parse_args().only)
```

Also print, per config, the 10 nodes with the largest absolute `loading` into `details` (slug and value), and put the chance rates for race (0.143) and gender (0.5) in the table header line.

- [ ] **Step 4: Run tests, then the baseline**

Run: `uv run pytest -q`
Expected: all pass

```bash
uv run python -m pipeline.build_index          # refresh image_vecs.npz with path/source arrays
uv run python -m pipeline.probe                # if not already run after the rebuild
uv run python -m pipeline.fairness --only centroid head head_rw
cat data/fairness_report.md
```
Expected: the `centroid` row reproduces top-5 ~0.72 (within 0.01 of `evaluate.py`), race TVD and recoverability well above chance. Record the centroid row as the "current" column in the spec's success table and set the TVD targets to half of it.

- [ ] **Step 5: Commit (if approved)**

```bash
git add pipeline/fairness.py pipeline/evaluate.py pipeline/tests/test_evaluate.py docs/superpowers/specs/2026-09-30-bias-mitigation-design.md
git commit -m "feat(pipeline): fairness report over scorer x treatment configs"
```

---

### Task 9: Fit the debias maps and masked index, run the full report

**Files:** none new; runs CLIs from Tasks 3, 5, 6, 8.

- [ ] **Step 1: Masked data**

```bash
uv run python -m pipeline.build_index --limit 5 --mask-faces --tag smoke && rm data/*_smoke.npz
uv run python -m pipeline.build_index --mask-faces --tag masked      # ~9.7k images, CPU, tens of minutes
uv run python -m pipeline.probe --mask-faces
```

- [ ] **Step 2: Debias maps**

```bash
uv run python -m pipeline.debias
```
Expected: three files, LEACE rank 512 - 7 = 505.

- [ ] **Step 3: Full report**

```bash
uv run python -m pipeline.fairness
cat data/fairness_report.md
```
Decide using the spec's success table: pick the row with the lowest race TVD among those with top-5 >= 0.69 and recoverability within 5 points of chance. If none clears the floor, the closest row is chosen and the gap reported to the user rather than quietly lowering the floor. Add `head+prompt` rows to `CONFIGS` only if `centroid+prompt` beat `centroid+leace`.

- [ ] **Step 4: Commit the report (if approved)**

```bash
git add data/fairness_report.md
git commit -m "docs: baseline and mitigation fairness report"
```
(Only if `data/` reports are tracked; otherwise paste the table into the PR or summary.)

---

### Task 10: Serve the chosen configuration

**Files:**
- Modify: `server/match.py` (`Index`, `Encoder`), `pipeline/build_index.py` (`--debias`, `--head`), `server/tests/test_server.py`, `Dockerfile` (copy the ONNX model is not needed: it lives in `DATA_DIR`).

**Interfaces:**
- `Index` gains optional fields `proj_P (d,d)`, `proj_b (d,)`, `head_w (m,d) | None`, `head_b (m,) | None`, `masked_faces: bool`. `Index.load` reads them when present. `Index.scores(vec)` applies the projection to the query; with a head it returns `where(counts < MIN_IMAGES, zscore(txt), zscore(logits)) + PRIOR_WEIGHT * prior`, otherwise the existing blend.
- `Encoder(masked: bool = False)` builds a `Detector` when masked (so a missing model fails at startup) and masks before preprocessing.
- `build_index.py --debias {none,prompt,leace} --head {none,plain,reweighted}` stores `proj_P`, `proj_b`, `head_w`, `head_b`. Centroids and text vectors are stored **untreated**; `Index.__post_init__` applies the map, so one index file holds raw data plus the map.

- [ ] **Step 1: Write the failing tests**

```python
# append to server/tests/test_server.py
from pipeline.train_head import zscore


def test_index_without_new_keys_scores_as_before(tmp_path):
    np.savez(tmp_path / "i.npz", slugs=np.array(INDEX.slugs), centroids=INDEX.centroids, text_vecs=INDEX.text_vecs,
             counts=INDEX.counts, xy=INDEX.xy, mean_img=np.zeros(3, np.float32), mean_txt=np.zeros(3, np.float32), prior=np.zeros(3, np.float32))
    loaded = Index.load(tmp_path / "i.npz")
    q = normalize(np.array([1, 0.2, 0], np.float32))
    np.testing.assert_allclose(loaded.scores(q), INDEX.scores(q), atol=1e-6)
    assert loaded.masked_faces is False and loaded.head_w is None


def test_projection_applies_to_query_and_centroids():
    P = np.diag([0, 1, 1]).astype(np.float32)  # erase axis 0
    idx = Index(slugs=INDEX.slugs, centroids=INDEX.centroids, text_vecs=INDEX.text_vecs, counts=INDEX.counts, xy=INDEX.xy,
                proj_P=P, proj_b=np.zeros(3, np.float32))
    s = idx.scores(np.array([1, 0, 0], np.float32))
    assert abs(s[0] - s[1]) < 1e-6  # red and green are indistinguishable once axis 0 is gone


def test_head_scores_use_logits_and_text_fallback_on_same_scale():
    head_w = np.array([[5, 0, 0], [0, 5, 0], [0, 0, 0]], np.float32)
    idx = Index(slugs=INDEX.slugs, centroids=INDEX.centroids, text_vecs=INDEX.text_vecs, counts=INDEX.counts, xy=INDEX.xy,
                head_w=head_w, head_b=np.zeros(3, np.float32))
    s = idx.scores(np.array([1, 0, 0], np.float32))
    assert s.argmax() == 0
    expected_text = zscore((normalize(idx.text_vecs) @ np.array([1, 0, 0], np.float32))[None])[0, 2]
    assert abs(s[2] - expected_text) < 1e-5


def test_masked_encoder_requires_detector(monkeypatch, tmp_path):
    from server.match import Encoder
    import pipeline.faces as faces
    monkeypatch.setattr(faces, "MODEL_PATH", tmp_path / "missing.onnx")
    with pytest.raises(FileNotFoundError):
        Encoder(masked=True)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest server/tests/test_server.py -v`
Expected: 4 new FAIL (`Index` has no `proj_P` field, etc.)

- [ ] **Step 3: Implement in `server/match.py`**

```python
from pipeline.train_head import zscore

MIN_IMAGES = 3  # must match pipeline.build_index.MIN_IMAGES


@dataclass
class Index:
    slugs: list[str]
    centroids: np.ndarray
    text_vecs: np.ndarray
    counts: np.ndarray
    xy: np.ndarray
    mean_img: np.ndarray | None = None
    mean_txt: np.ndarray | None = None
    prior: np.ndarray | None = None
    proj_P: np.ndarray | None = None  # affine debias map; None = identity
    proj_b: np.ndarray | None = None
    head_w: np.ndarray | None = None  # linear head; None = nearest centroid
    head_b: np.ndarray | None = None
    masked_faces: bool = False

    def __post_init__(self):
        d = self.centroids.shape[1]
        self.proj_P = np.eye(d, np.float32) if self.proj_P is None else self.proj_P
        self.proj_b = np.zeros(d, np.float32) if self.proj_b is None else self.proj_b
        self.mean_img = np.zeros(d, np.float32) if self.mean_img is None else self.mean_img
        self.mean_txt = np.zeros(d, np.float32) if self.mean_txt is None else self.mean_txt
        self.prior = np.zeros(len(self.slugs), np.float32) if self.prior is None else self.prior
        self.mean_img, self.mean_txt = self._proj(self.mean_img), self._proj(self.mean_txt)
        self._img = normalize(self._proj(self.centroids) - self.mean_img)
        self._txt = normalize(self._proj(self.text_vecs) - self.mean_txt)

    def _proj(self, v):
        return (v @ self.proj_P.T + self.proj_b).astype(np.float32)

    @classmethod
    def load(cls, path: Path) -> "Index":
        z = np.load(path)
        opt = {k: z[k] for k in ("proj_P", "proj_b", "head_w", "head_b") if k in z.files}
        return cls(list(z["slugs"]), z["centroids"], z["text_vecs"], z["counts"], z["xy"], z["mean_img"], z["mean_txt"], z["prior"],
                   masked_faces=bool(z["masked_faces"]) if "masked_faces" in z.files else False, **opt)

    def scores(self, vec: np.ndarray) -> np.ndarray:
        vec = self._proj(vec)
        txt = self._txt @ normalize(vec - self.mean_txt)
        if self.head_w is not None:
            logits = zscore((vec @ self.head_w.T + self.head_b)[None])[0]
            return np.where(self.counts < MIN_IMAGES, zscore(txt[None])[0], logits) + PRIOR_WEIGHT * self.prior
        img = self._img @ normalize(vec - self.mean_img)
        return np.where(self.counts > 0, IMAGE_WEIGHT * img + TEXT_WEIGHT * txt, txt) + PRIOR_WEIGHT * self.prior
```

`Encoder`:

```python
class Encoder:
    def __init__(self, masked: bool = False):
        from pipeline.build_index import load_model

        self.model, self.preprocess, _, self.torch = load_model()
        self.masker = None
        if masked:
            from pipeline.faces import Detector
            self.masker = Detector()  # raises at startup if the model file is missing

    def encode(self, data: bytes) -> np.ndarray:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        if self.masker:
            img = self.masker.mask(img)
        ...
```

In `server/app.py` `load()`: `state.setdefault("encoder", Encoder(masked=state["index"].masked_faces))`.

Note the test `test_head_scores_use_logits_and_text_fallback_on_same_scale` expects `txt` for the text-only node computed against `normalize(text_vecs)` with zero means, which is what the fixture gives; keep `MIN_IMAGES = 3` so the fixture's `counts=[5,5,0]` makes only node 2 a fallback.

- [ ] **Step 4: `build_index.py` flags**

```python
    ap.add_argument("--debias", choices=["none", "prompt", "leace"], default="none")
    ap.add_argument("--head", choices=["none", "plain", "reweighted"], default="none")
```
In `main`, after computing `image_vecs` and before `np.savez`:

```python
    extra = {}
    if debias != "none":
        t = np.load(DATA / f"debias_{debias}{'_masked' if mask_faces and debias == 'leace' else ''}.npz")
        extra = {"proj_P": t["P"], "proj_b": t["b"]}
    if head != "none":
        from pipeline.debias import apply
        from pipeline.train_head import group_weights, train
        owner_idx = np.array([slugs.index(o) for o in owner])
        treated = apply(image_vecs, extra["proj_P"], extra["proj_b"]) if extra else image_vecs
        w = group_weights(np.load(DATA / "reference_attrs.npz")["race"][source], owner_idx) if head == "reweighted" else None
        extra["head_w"], extra["head_b"] = train(treated, owner_idx, len(slugs), w)
```
and pass `**extra` into the `index.npz` savez. The head is trained on treated vectors because `Index.scores` projects the query before applying the head. `reference_attrs.npz` is aligned to the untagged `image_vecs.npz` originals, so index it by `source` (row to original image) as shown.

- [ ] **Step 5: Run tests, rebuild with the chosen configuration, smoke the server**

Run: `uv run pytest -q`
Expected: all pass

```bash
uv run python -m pipeline.build_index --limit 5 --crops 1 --debias leace --head reweighted --tag smoke && rm data/*_smoke.npz
uv run python -m pipeline.build_index --crops 2 --debias leace --head reweighted [--mask-faces]   # flags per Task 9's winner
uv run uvicorn server.app:app --port 8001 &
curl -s -F images=@$(find data/img -name '*.jpg' | head -1) localhost:8001/api/analyze | head -c 400; kill %1
uv run python -m pipeline.fairness --only centroid   # sanity: same numbers as before on the rebuilt raw data
```

- [ ] **Step 6: Commit (if approved)**

```bash
git add server/match.py server/app.py pipeline/build_index.py server/tests/test_server.py
git commit -m "feat: serve debiased index with optional linear head and face masking"
```

Then rebuild the container (`docker compose build && docker compose up -d`) only when the user says to deploy.

---

## Self-review notes

- Spec coverage: probe (T6), metrics (T2, T8), prompt projection and LEACE (T3), face masking (T4, T5), reweighting (T7), head with crops (T5, T7), configurations table (T8), serving (T10), dependencies (T1), error handling: thin cell abort (T6), noisy-label warning (T8), ridge in LEACE (T3), missing detector model (T4, T10), order of work (T8, T9, T10). Node loading top-10 printing is in T8 step 3.
- Type consistency: `apply(vecs, P, b)` used identically in T3, T8, T10; `group_weights(groups, owner_idx)` in T7, T8, T10; `cv_scores(X, owner_idx, n_classes, source, weights)` in T7 and T8; `zscore` in T7, T8, T10; `image_vecs.npz` keys `vecs, owner, path, source` in T5, T6, T8, T10.
- Review focus coverage: 1 in T6, 2 in T6 and T7, 3 in T4 and T10, 4 in T10, 5 in T7.
