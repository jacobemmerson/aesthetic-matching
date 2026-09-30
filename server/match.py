"""Score uploaded images against the aesthetic index and place them on the graph."""
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

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

    def __post_init__(self):
        self.mean_img = np.zeros(self.centroids.shape[1], np.float32) if self.mean_img is None else self.mean_img
        self.mean_txt = np.zeros(self.text_vecs.shape[1], np.float32) if self.mean_txt is None else self.mean_txt
        self.prior = np.zeros(len(self.slugs), np.float32) if self.prior is None else self.prior
        self._img = normalize(self.centroids - self.mean_img)
        self._txt = normalize(self.text_vecs - self.mean_txt)

    @classmethod
    def load(cls, path: Path) -> "Index":
        z = np.load(path)
        return cls(list(z["slugs"]), z["centroids"], z["text_vecs"], z["counts"], z["xy"], z["mean_img"], z["mean_txt"], z["prior"])

    def scores(self, vec: np.ndarray) -> np.ndarray:
        """Blend of centered image-centroid and text similarity; nodes without images use text only."""
        img = self._img @ normalize(vec - self.mean_img)
        txt = self._txt @ normalize(vec - self.mean_txt)
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

    def __init__(self):
        from pipeline.build_index import load_model

        self.model, self.preprocess, _, self.torch = load_model()

    def encode(self, data: bytes) -> np.ndarray:
        img = Image.open(io.BytesIO(data)).convert("RGB")  # raises on non-images; caller maps to 400
        with self.torch.no_grad():
            v = self.model.encode_image(self.preprocess(img).unsqueeze(0)).float().numpy()[0]
        return v / np.linalg.norm(v)
