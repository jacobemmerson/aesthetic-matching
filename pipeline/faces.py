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
