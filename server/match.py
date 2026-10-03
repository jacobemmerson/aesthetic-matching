"""Score uploaded images against the aesthetic index and place them on the graph."""
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from pipeline.build_index import MIN_IMAGES
from pipeline.train_head import zscore

IMAGE_WEIGHT, TEXT_WEIGHT = 0.7, 0.3
PRIOR_WEIGHT = 0.08  # from pipeline/evaluate.py: +2pts popularity-weighted top-1 for -0.6pt plain
TOP_K = 5
SOFTMAX_T = 0.01  # the contrastive logit scale (100 x cosine); turns scores into per-photo probabilities
HEAD_SOFTMAX_T = 0.16  # z-scored head logits: measured #1-#2 gaps are ~16x the cosine gaps (0.78 vs 0.048 median)
TIE_RATIO = 1 / 3  # a runner-up is a label too when it has at least this share of the top match's probability
PLACE_NUDGE = (0.06, 0.03)  # how far the map position leans from the top match toward #2 and #3; small, so the nearest node is always the label


def normalize(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-8)


@dataclass
class Index:
    slugs: list[str]
    centroids: np.ndarray
    text_vecs: np.ndarray
    counts: np.ndarray
    xyz: np.ndarray  # unit vectors on the map sphere
    mean_img: np.ndarray | None = None  # dataset means; None means "already centered" (tests)
    mean_txt: np.ndarray | None = None
    prior: np.ndarray | None = None  # how well known each aesthetic is, in [0, 1]; None = flat
    proj_P: np.ndarray | None = None  # affine debias map applied to every vector; None = identity
    proj_b: np.ndarray | None = None
    head_w: np.ndarray | None = None  # linear head; None = nearest centroid
    head_b: np.ndarray | None = None
    masked_faces: bool = False  # index was built from face-masked images, so mask uploads too
    backbone: tuple[str, str] = ("ViT-B-32", "laion2b_s34b_b79k")  # (open_clip model, pretrained) the vectors came from; files without the field predate SigLIP

    def __post_init__(self):
        d = self.centroids.shape[1]
        self.proj_P = np.eye(d, dtype=np.float32) if self.proj_P is None else self.proj_P
        self.proj_b = np.zeros(d, np.float32) if self.proj_b is None else self.proj_b
        self.mean_img = np.zeros(d, np.float32) if self.mean_img is None else self.mean_img
        self.mean_txt = np.zeros(d, np.float32) if self.mean_txt is None else self.mean_txt
        self.prior = np.zeros(len(self.slugs), np.float32) if self.prior is None else self.prior
        self.mean_img, self.mean_txt = self._proj(self.mean_img), self._proj(self.mean_txt)
        self._img = normalize(self._proj(self.centroids) - self.mean_img)
        self._txt = normalize(self._proj(self.text_vecs) - self.mean_txt)

    def _proj(self, v: np.ndarray) -> np.ndarray:
        return (v @ self.proj_P.T + self.proj_b).astype(np.float32)

    @classmethod
    def load(cls, path: Path) -> "Index":
        z = np.load(path)
        optional = {k: z[k] for k in ("proj_P", "proj_b", "head_w", "head_b") if k in z.files}
        masked = bool(z["masked_faces"]) if "masked_faces" in z.files else False
        if "model" in z.files:
            optional["backbone"] = (str(z["model"]), str(z["pretrained"]))
        return cls(list(z["slugs"]), z["centroids"], z["text_vecs"], z["counts"], z["xyz"], z["mean_img"], z["mean_txt"], z["prior"],
                   masked_faces=masked, **optional)

    def scores(self, vec: np.ndarray) -> np.ndarray:
        """Head logits when a head is present, else a blend of centered image-centroid and text
        similarity; nodes without enough images use text only. Head logits and text scores are
        z-scored so the prior means the same thing on both."""
        vec = self._proj(vec)
        txt = self._txt @ normalize(vec - self.mean_txt)
        if self.head_w is not None:
            logits = zscore((vec @ self.head_w.T + self.head_b)[None])[0]
            return np.where(self.counts < MIN_IMAGES, zscore(txt[None])[0], logits) + PRIOR_WEIGHT * self.prior
        img = self._img @ normalize(vec - self.mean_img)
        return np.where(self.counts > 0, IMAGE_WEIGHT * img + TEXT_WEIGHT * txt, txt) + PRIOR_WEIGHT * self.prior

    def place(self, slugs: list[str]) -> dict:
        """Map position for an ordered list of aesthetics: anchored at the first so the label and
        the position agree (a weighted mean of three nodes could land beside an unrelated fourth),
        nudged toward the next two."""
        idx = [self.slugs.index(s) for s in slugs]
        anchor = self.xyz[idx[0]]
        x, y, z = normalize(anchor + sum(w * (self.xyz[i] - anchor) for w, i in zip(PLACE_NUDGE, idx[1:])))
        return {"x": float(x), "y": float(y), "z": float(z)}

    def match(self, vec: np.ndarray) -> dict:
        s = self.scores(vec)
        z = np.exp((s - s.max()) / (HEAD_SOFTMAX_T if self.head_w is not None else SOFTMAX_T))
        prob = z / z.sum()
        top = np.argsort(-s)[:TOP_K]
        return {"matches": [{"slug": self.slugs[i], "score": float(s[i]), "prob": float(prob[i])} for i in top],
                **self.place([self.slugs[i] for i in top])}


def labels(matches: list[dict], ratio: float = TIE_RATIO) -> list[str]:
    """A photo's aesthetics: the top match plus any runner-up within `ratio` of it. A photo can
    carry two aesthetics; a distant second is not one of them."""
    top = matches[0]["prob"]
    return [m["slug"] for m in matches if m["prob"] >= ratio * top]


def mixture(image_results: list[dict]) -> list[dict]:
    """The upload's overall distribution: the photos' distributions averaged, so a mix stays a mix
    instead of collapsing to whatever direction the embeddings share."""
    mass: dict[str, float] = {}
    for r in image_results:
        for m in r["matches"]:
            mass[m["slug"]] = mass.get(m["slug"], 0.0) + m["prob"] / len(image_results)
    return [{"slug": s, "prob": round(p, 4)} for s, p in sorted(mass.items(), key=lambda kv: -kv[1])]


def verdict(image_results: list[dict], cap: int = 5) -> list[dict]:
    """Every label any photo carries, with the photos that carry it, by probability mass."""
    mass: dict[str, float] = {}
    photos: dict[str, list[int]] = {}
    for i, r in enumerate(image_results):
        probs = {m["slug"]: m["prob"] for m in r["matches"]}
        for s in labels(r["matches"]):
            mass[s] = mass.get(s, 0.0) + probs[s]
            photos.setdefault(s, []).append(i)
    rows = sorted(mass, key=lambda s: (-mass[s], -len(photos[s]), photos[s][0]))
    return [{"slug": s, "photos": photos[s]} for s in rows[:cap]]


def basic_score(image_results: list[dict], ratings: dict[str, float]) -> int:
    """0 = the most niche thing in the catalog, 100 = the most basic; probability-weighted mean
    of the mainstream ratings over each photo's matches, rescaled over the catalog's range."""
    lo, hi = (min(ratings.values()), max(ratings.values())) if ratings else (0.0, 0.0)
    pairs = [(max(m["prob"], 1e-6), ratings[m["slug"]]) for r in image_results for m in r["matches"] if m["slug"] in ratings]
    if hi <= lo or not pairs:
        return 50
    mean = sum(w * v for w, v in pairs) / sum(w for w, _ in pairs)
    return int(min(100, max(0, round((mean - lo) / (hi - lo) * 100))))


class Encoder:
    """Image encoder (open_clip backbone), loaded once. Kept separate so tests can swap in a fake."""

    def __init__(self, masked: bool = False, backbone: tuple[str, str] | None = None):
        from pipeline.build_index import load_model

        self.masker = None
        if masked:
            from pipeline.faces import Detector

            self.masker = Detector()  # before the backbone so a missing model file fails fast at startup
        self.model, self.preprocess, _, self.torch = load_model(*backbone) if backbone else load_model()

    def encode(self, data: bytes) -> np.ndarray:
        img = Image.open(io.BytesIO(data)).convert("RGB")  # raises on non-images; caller maps to 400
        if self.masker:
            img = self.masker.mask(img)
        with self.torch.no_grad():
            v = self.model.encode_image(self.preprocess(img).unsqueeze(0)).float().numpy()[0]
        return v / np.linalg.norm(v)
