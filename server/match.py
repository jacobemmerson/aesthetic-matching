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
SOFTMAX_T = 0.01  # CLIP's own logit scale (100 x cosine); turns scores into per-photo probabilities
NUCLEUS_P = 0.9   # a photo is explained by the fewest aesthetics whose probabilities reach this
PLACE_NUDGE = (0.2, 0.1)  # how far the map position leans from the top match toward #2 and #3


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
    backbone: tuple[str, str] = ("ViT-B-32", "laion2b_s34b_b79k")  # (open_clip model, pretrained) the vectors came from

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

    def match(self, vec: np.ndarray) -> dict:
        s = self.scores(vec)
        z = np.exp((s - s.max()) / SOFTMAX_T)
        prob = z / z.sum()
        top = np.argsort(-s)[:TOP_K]
        # Anchor at the top match so the label and the map position agree (a weighted mean of
        # three nodes could land beside an unrelated fourth); the nudges hint at the runners-up.
        anchor = self.xyz[top[0]]
        x, y, z = normalize(anchor + sum(w * (self.xyz[i] - anchor) for w, i in zip(PLACE_NUDGE, top[1:])))
        return {"matches": [{"slug": self.slugs[i], "score": float(s[i]), "prob": float(prob[i])} for i in top],
                "x": float(x), "y": float(y), "z": float(z)}


def aggregate(vecs: list[np.ndarray]) -> np.ndarray:
    """One unit vector for the whole upload, scored like a photo."""
    return normalize(np.mean(vecs, axis=0))


def nucleus(matches: list[dict], p: float = NUCLEUS_P) -> list[str]:
    """Top-p over the listed matches: the fewest slugs whose probabilities reach p."""
    out, total = [], 0.0
    for m in matches:
        out.append(m["slug"])
        total += m["prob"]
        if total >= p:
            break
    return out


def cover(image_results: list[dict], seed: str, p: float = NUCLEUS_P, cap: int = 5) -> list[dict]:
    """Smallest set of aesthetics that explains every photo, where a photo is explained by any
    aesthetic in its nucleus (so clear winners stand alone and near-ties merge). Greedy, seeded
    with the aggregate's best match; grows with how diverse the photos are. Rows are sorted by
    photos explained, then probability mass."""
    nuclei = [{m["slug"]: m["prob"] for m in r["matches"] if m["slug"] in nucleus(r["matches"], p)} for r in image_results]
    uncovered = set(range(len(nuclei)))
    chosen = [seed]
    while True:
        uncovered -= {i for i in uncovered if chosen[-1] in nuclei[i]}
        if not uncovered or len(chosen) >= cap:
            break
        candidates = {s for i in uncovered for s in nuclei[i]}
        chosen.append(max(candidates, key=lambda s: (sum(s in n for n in nuclei), sum(n.get(s, 0) for n in nuclei),
                                                     -min(i for i in uncovered if s in nuclei[i]))))
    found = [{"slug": s, "photos": [i for i, n in enumerate(nuclei) if s in n]} for s in chosen if any(s in n for n in nuclei)]
    return sorted(found, key=lambda a: (-len(a["photos"]), -sum(nuclei[i][a["slug"]] for i in a["photos"])))


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
    """CLIP image encoder, loaded once. Kept separate so tests can swap in a fake."""

    def __init__(self, masked: bool = False, backbone: tuple[str, str] | None = None):
        from pipeline.build_index import load_model

        self.masker = None
        if masked:
            from pipeline.faces import Detector

            self.masker = Detector()  # before CLIP so a missing model file fails fast at startup
        self.model, self.preprocess, _, self.torch = load_model(*backbone) if backbone else load_model()

    def encode(self, data: bytes) -> np.ndarray:
        img = Image.open(io.BytesIO(data)).convert("RGB")  # raises on non-images; caller maps to 400
        if self.masker:
            img = self.masker.mask(img)
        with self.torch.no_grad():
            v = self.model.encode_image(self.preprocess(img).unsqueeze(0)).float().numpy()[0]
        return v / np.linalg.norm(v)
