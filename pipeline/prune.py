"""Reference-set hygiene: drop near-duplicate images within a node and images that are mostly a
face (they encode who was photographed, not the aesthetic)."""
import numpy as np

DUPLICATE_COSINE = 0.95
MAX_FACE_FRACTION = 1 / 3


def near_duplicates(vecs: np.ndarray, owner: list[str], threshold: float = DUPLICATE_COSINE) -> np.ndarray:
    """True for rows that repeat an earlier row of the same node (cosine above threshold)."""
    dup = np.zeros(len(vecs), bool)
    for slug in set(owner):
        idx = [i for i, o in enumerate(owner) if o == slug]
        sims = vecs[idx] @ vecs[idx].T
        for a in range(len(idx)):
            if dup[idx[a]]:
                continue
            for b in range(a + 1, len(idx)):
                if sims[a, b] > threshold:
                    dup[idx[b]] = True
    return dup


def face_fraction(boxes: list[tuple[int, int, int, int]], width: int, height: int) -> float:
    return max((w * h for _, _, w, h in boxes), default=0) / (width * height)
