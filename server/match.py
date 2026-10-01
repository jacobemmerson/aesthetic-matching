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
PLACE_K = 3


def normalize(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-8)


@dataclass
class Index:
    slugs: list[str]
    centroids: np.ndarray
    text_vecs: np.ndarray
    counts: np.ndarray
    xy: np.ndarray
    mean_img: np.ndarray | None = None  # dataset means; None means "already centered" (tests)
    mean_txt: np.ndarray | None = None
    prior: np.ndarray | None = None  # how well known each aesthetic is, in [0, 1]; None = flat
    proj_P: np.ndarray | None = None  # affine debias map applied to every vector; None = identity
    proj_b: np.ndarray | None = None
    head_w: np.ndarray | None = None  # linear head; None = nearest centroid
    head_b: np.ndarray | None = None
    masked_faces: bool = False  # index was built from face-masked images, so mask uploads too

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
        return cls(list(z["slugs"]), z["centroids"], z["text_vecs"], z["counts"], z["xy"], z["mean_img"], z["mean_txt"], z["prior"],
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
        top = np.argsort(-s)[:TOP_K]
        weights = np.clip(s[top[:PLACE_K]], 1e-6, None)
        x, y = (self.xy[top[:PLACE_K]] * weights[:, None]).sum(0) / weights.sum()
        return {"matches": [{"slug": self.slugs[i], "score": float(s[i])} for i in top], "x": float(x), "y": float(y)}


def overall(image_results: list[dict], top_k: int = 3) -> list[dict]:
    """Each photo's best match first (so every photo is represented), then the highest summed
    scores. Plain summing let one photo's cluster of near-synonyms fill every slot."""
    totals: dict[str, float] = {}
    for r in image_results:
        for m in r["matches"]:
            totals[m["slug"]] = totals.get(m["slug"], 0.0) + m["score"]
    firsts = sorted({r["matches"][0]["slug"] for r in image_results}, key=lambda s: -totals[s])
    rest = sorted((s for s in totals if s not in firsts), key=lambda s: -totals[s])
    return [{"slug": s, "score": totals[s]} for s in (firsts + rest)[:top_k]]


class Encoder:
    """CLIP image encoder, loaded once. Kept separate so tests can swap in a fake."""

    def __init__(self, masked: bool = False):
        from pipeline.build_index import load_model

        self.masker = None
        if masked:
            from pipeline.faces import Detector

            self.masker = Detector()  # before CLIP so a missing model file fails fast at startup
        self.model, self.preprocess, _, self.torch = load_model()

    def encode(self, data: bytes) -> np.ndarray:
        img = Image.open(io.BytesIO(data)).convert("RGB")  # raises on non-images; caller maps to 400
        if self.masker:
            img = self.masker.mask(img)
        with self.torch.no_grad():
            v = self.model.encode_image(self.preprocess(img).unsqueeze(0)).float().numpy()[0]
        return v / np.linalg.norm(v)
