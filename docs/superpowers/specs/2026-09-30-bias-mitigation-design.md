# Bias mitigation and linear head for aesthetic matching

Date: 2026-09-30

## Problem

Matching is nearest-centroid over frozen CLIP ViT-B/32 embeddings (397 nodes, ~9,700 Google
Images references, ~25 per node). Non-white faces are routed to stereotyped nodes: Black faces to
"gang" style aesthetics, and the same pattern for Asian, Native American, Arab and other BIPOC
faces toward the nodes whose reference images happen to feature them. Cause: Google Images
references for those nodes are mostly portraits of one group, so the centroid encodes skin tone
and facial features, and CLIP itself carries documented race and gender bias. Nothing currently
measures this.

## Goals

1. Measure race and gender bias in the matcher with a repeatable number.
2. Reduce it below a target without dropping accuracy below a floor.
3. Replace nearest-centroid with a linear head where that improves accuracy.

Out of scope for this spec: the deny list for offensive or niche nodes, synthetic counterfactual
images, fine-tuning the CLIP towers. The node-loading numbers produced here feed the deny list
later.

## Success criteria

Measured on the FairFace probe and the existing leave-one-out evaluation:

| metric | current | target |
|---|---|---|
| top-1 label parity, max TVD across race groups | unknown (baseline run first) | halved from baseline |
| top-1 label parity, max TVD across gender groups | unknown | halved from baseline |
| race recoverable from embedding (5-fold logreg acc.) | unknown | within 5 points of chance (1/7) |
| gender recoverable from embedding | unknown | within 5 points of chance (1/2) |
| leave-one-out top-5 (plain) | 0.72 | >= 0.69 (floor: at most 3 points lost) |

The baseline run sets the "current" column; targets are revised there if the baseline says they
are unreachable or trivial.

## Attributes

Race: the seven FairFace groups (White, Black, Latino/Hispanic, East Asian, Southeast Asian,
Indian, Middle Eastern). Gender: FairFace's two. Both erased jointly, and parity is the worst group, so
skew against any group fails the target equally. Per-group counts are always printed so thin
groups are visible rather than hidden.

Known limitation: FairFace has no Native American group, so those faces are labeled as one of
the seven (usually Latino/Hispanic or East Asian) and that bias is measured only indirectly. A
supplementary probe set is a follow-up if the deny-list work or user reports show it matters.

## Components

All new code lives in `pipeline/`; the server changes are one optional projection matrix and one
optional face-mask call.

### 1. Probe data: `pipeline/probe.py`

- Downloads the FairFace validation split (~11k face crops, race x gender x age labels) via the
  `datasets` package from the HuggingFace mirror. Seeded sample of 200 per race x gender cell
  (2,800 images; cells with fewer are taken whole and the shortfall printed).
- Embeds with the same `load_model()` encoder as the index. Writes `data/probe.npz`:
  `vecs (n,512)`, `race (n,)`, `gender (n,)`, `id (n,)`.
- Labels the reference images: a multinomial logistic regression (torch, no new dependency) is
  trained on the probe embeddings for race and for gender, and applied to
  `data/image_vecs.npz`. Held-out FairFace accuracy of that classifier is printed and stored, so
  the noise in reference labels is known. Reference images with no detected face (section 3,
  face detector) get `none`. Writes `data/reference_attrs.npz`: `race`, `gender`,
  `race_conf`, `gender_conf`, aligned with `image_vecs.npz`.
- `--limit N` embeds only N probe images for a smoke run.

### 2. Metrics: `pipeline/fairness.py`

One function per metric, all pure numpy over arrays, so tests use synthetic vectors.

- `parity(top1_labels, groups)`: per-group top-1 label distribution over nodes; returns the max
  total-variation distance across groups and, per group, the 10 nodes most over-represented
  relative to the pooled distribution (the "gang for Black faces" number made concrete).
- `recoverability(vecs, labels)`: 5-fold logistic regression accuracy predicting the attribute
  from the embeddings, alongside chance and majority-class rates.
- `node_loading(centroids, directions)`: cosine of each centroid with each attribute direction,
  ranked. Directions come from the probe set (group mean differences) so this needs no prompts.
- Accuracy floor reuses `pipeline/evaluate.py` unchanged.
- `main()` runs every registered configuration (section 5) and prints one table: rows are
  configurations, columns are race TVD, gender TVD, race acc, gender acc, LOO top-1, LOO top-5.
  Also writes the table to `data/fairness_report.md` so runs can be compared over time.

### 3. Mitigations

Each mitigation is either a function `f(vecs) -> vecs` applied identically to reference
embeddings, centroids, text vectors and queries, or a change to what gets embedded. They compose.

- **Prompt projection** (`pipeline/debias.py: prompt_directions`, `project_out`). For each
  attribute, embed paired prompts ("a photo of a Black person" / "a photo of a white person",
  several templates, all group pairs) and take the difference vectors. Race gives a small
  subspace (top-k singular vectors of the differences, k = groups - 1), gender one direction.
  Orthogonalize the stacked subspace and project it out. Needs no labels. This is the baseline
  the label-supervised method must beat.
- **LEACE** (`pipeline/debias.py: leace_fit`). Fit on `probe.npz` for race and gender jointly
  (one-hot concatenated). Implemented in numpy from the paper's closed form (whitening, then
  projection onto the label-covariance subspace, then unwhitening); about 20 lines. The
  `concept-erasure` package is not added. Returns an affine map `(P, b)` applied as
  `vecs @ P.T + b`.
- **Face masking** (`pipeline/faces.py`). OpenCV's YuNet detector (`opencv-python-headless`,
  model file `face_detection_yunet_2023mar.onnx` downloaded once into `data/`). Every detected
  face box is expanded by 20% and filled with the image's mean colour, then the image is
  embedded as usual. Applied to reference images at index build (`build_index.py --mask-faces`,
  writing `image_vecs.npz` from masked images) and, when the index says it was built masked, to
  uploads in `Encoder.encode`. The detector's face count per reference image is what section 1
  uses to assign `none`.
- **Group reweighting** (inside the head, section 4). Each reference image gets weight
  `global_share(group) / node_share(group)` clipped to [0.2, 5], so within every node the
  effective group mix matches the whole dataset. Images labeled `none` get weight 1.

### 4. Linear head: `pipeline/train_head.py`

- Multinomial logistic regression over the 512-d embeddings, 397 classes, L2-regularized, torch
  on CPU (~10k rows; seconds). Regularization strength picked by 5-fold CV over images, the
  leave-one-out numbers in `evaluate.py` are replaced by the CV fold predictions for the head
  rows of the report.
- Random-crop augmentation: `build_index.py --crops K` embeds K additional random crops
  (scale 0.5 to 0.9) per reference image into `image_vecs.npz` with the same owner. Crops of an
  image stay in the same CV fold. Crops are an accuracy aid only; they do not touch bias.
- Optional sample weights (reweighting above).
- Output stored in `index.npz` as `head_w (397,512)`, `head_b (397,)`. Nodes with fewer than
  `MIN_IMAGES` references keep the text-vector fallback: their head row is masked out and the
  text score used, matching the existing centroid fallback.

### 5. Configurations compared

The report crosses scorer x embedding treatment:

| scorer | treatment |
|---|---|
| centroid (current) | none (baseline) |
| centroid | prompt projection |
| centroid | LEACE |
| centroid | face mask |
| centroid | face mask + LEACE |
| head plain | none |
| head reweighted | none |
| head reweighted | LEACE |
| head reweighted | face mask + LEACE |

Head rows on prompt projection are added only if prompt projection beats LEACE on centroids.
Prior weight and image/text blend stay at their current values throughout; retuning them is a
separate pass after a treatment is chosen.

### 6. Serving changes (`server/match.py`, `pipeline/build_index.py`)

- `build_index.py` gains `--debias {none,prompt,leace}`, `--mask-faces`, `--crops K`,
  `--head {none,plain,reweighted}`. It writes the chosen affine map as `proj_P`, `proj_b` (identity
  and zero when none), `masked_faces` flag, and head weights when trained.
- `Index.__post_init__` applies the map to centroids and text vectors; `Index.scores` applies it
  to the query, then uses head logits when `head_w` is present, otherwise the existing blend.
  Head logits are z-scored per query before the prior is added so `PRIOR_WEIGHT` keeps meaning.
- `Encoder.encode` masks faces first when the index flag says so. Detector failure (no model
  file, decode error) raises at startup rather than silently serving unmasked.
- Existing `index.npz` without the new keys still loads: missing keys mean identity map, no
  mask, no head.

### 7. Dependencies added

- `datasets` (FairFace download, pipeline only)
- `opencv-python-headless` (YuNet face detection; server too when masking is on)

Logistic regression is done in torch, already installed; scikit-learn is not added.

## Data flow

```
FairFace (HF) --probe.py--> probe.npz --+--> fairness.py (parity, recoverability, loading)
                                        +--> debias.py (LEACE fit) --> proj_P, proj_b
                                        +--> attribute classifier --> reference_attrs.npz
data/img --[faces.py mask]--> build_index.py --> image_vecs.npz, index.npz (+proj, +head)
image_vecs.npz + reference_attrs.npz --> train_head.py --> head_w, head_b
index.npz --> server/match.py (apply proj, head or centroid) <-- Encoder (+mask)
```

## Error handling

- FairFace download failure or a cell with fewer than 20 images aborts `probe.py` with the
  counts printed; nothing downstream runs on a lopsided probe.
- Attribute classifier held-out accuracy below 0.6 for race or 0.85 for gender prints a warning
  in the report header: reference labels are then too noisy to trust reweighting numbers.
- LEACE fit with a singular covariance falls back to ridge-regularized whitening (`+1e-4 I`).
- Face detector: image with no face passes through unchanged (no error). Model file missing
  raises immediately.

## Testing

Pure functions get one small pytest each in `pipeline/tests/`, on synthetic vectors:

- `parity`: two groups with identical label distributions give TVD 0; disjoint give 1.
- `recoverability`: labels planted along one axis are recovered near 1.0; after `project_out`
  of that axis, near chance.
- `leace_fit`: after applying the map, the label-conditional means coincide (the LEACE
  guarantee), and rank of `P` is `d - (groups - 1)`.
- `train_head`: a linearly separable toy set reaches ~1.0 CV accuracy; reweighting a
  group-skewed toy set changes the fitted bias in the expected direction.
- `faces.mask`: a synthetic image with a known box is filled; an image with no face is
  returned unchanged (detector is mocked, the ONNX file is not needed in tests).
- `Index` round-trip: an index with `proj_P`, `head_w` loads and scores; one without still
  scores identically to today (regression guard against changing current behaviour).

Before any full run: `probe.py --limit 50`, `build_index.py --limit 5 --crops 1 --mask-faces`,
`fairness.py --limit` on those outputs, per the test-each-stage rule.

## Order of work

1. `probe.py`, `fairness.py`, baseline report on the current index. Fill in the "current"
   column and confirm the targets.
2. Prompt projection and LEACE on centroids; report.
3. Face masking; report (with and without LEACE).
4. Linear head with crops and reweighting; report.
5. Pick the configuration, wire the serving path, rebuild the index, redeploy.

Each step is its own commit and re-runs the report so regressions are caught at the step that
caused them.
