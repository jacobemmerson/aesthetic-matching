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


def load_fairface():
    from datasets import load_dataset

    ds = load_dataset("HuggingFaceM4/FairFace", "0.25", split="validation")
    race_names, gender_names = ds.features["race"].names, ds.features["gender"].names
    race = np.array([FAIRFACE_RACE[race_names[r]] for r in ds["race"]])
    gender = np.array([FAIRFACE_GENDER[gender_names[g]] for g in ds["gender"]])
    return ds, race, gender


def main(limit, per_cell, mask_faces, tag: str = ""):
    from PIL import Image

    from pipeline.build_index import load_model, normalize
    from pipeline.debias import suffix
    from pipeline.faces import Detector

    ds, race, gender = load_fairface()
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
    sfx = suffix(tag, mask_faces)
    np.savez(DATA / f"probe{sfx}.npz", vecs=normalize(np.concatenate(vecs)), race=race[idx], gender=gender[idx], id=idx.astype(str))
    print(f"wrote data/probe{sfx}.npz ({len(idx)} images)")
    if mask_faces:
        return  # reference labels come from the unmasked probe only
    ref = np.load(DATA / f"image_vecs{sfx}.npz")
    n = int(ref["source"].max()) + 1  # originals come first; crops map back through `source`
    n = n if limit is None else min(n, limit)
    det = Detector()
    has_face = np.array([len(det.boxes(Image.open(p))) > 0 for p in ref["path"][:n]])
    out = label_references(np.load(DATA / f"probe{sfx}.npz")["vecs"], race[idx], gender[idx], ref["vecs"][:n], has_face)
    print(f"attribute classifier held-out acc: race {out['race_cv_acc']:.3f} gender {out['gender_cv_acc']:.3f}; "
          f"{int((~has_face).sum())}/{len(has_face)} reference images without a face")
    np.savez(DATA / f"reference_attrs{sfx}.npz", **out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="smoke run: ~N probe images and N reference rows")
    ap.add_argument("--per-cell", type=int, default=200)
    ap.add_argument("--mask-faces", action="store_true", help="write probe_masked.npz instead")
    ap.add_argument("--tag", default="", help="suffix for a build made with another backbone (probe_TAG.npz, image_vecs_TAG.npz)")
    a = ap.parse_args()
    main(a.limit, a.per_cell, a.mask_faces, a.tag)
