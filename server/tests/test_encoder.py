import io
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from server.match import Encoder, preprocess

DATA = Path(__file__).resolve().parent.parent.parent / "data"
CFG = {"size": [224, 224], "mean": [0.5, 0.5, 0.5], "std": [0.5, 0.5, 0.5], "interpolation": "bicubic", "resize_mode": "squash"}
FIXTURE = Path(__file__).resolve().parent.parent.parent / "web" / "scripts" / "fixtures" / "photo1.jpg"


def test_preprocess_squashes_scales_and_normalises():
    x = preprocess(Image.new("RGB", (300, 100), (255, 0, 128)), CFG)
    assert x.shape == (1, 3, 224, 224) and x.dtype == np.float32
    assert x[0, 0].max() == pytest.approx(1.0) and x[0, 1].min() == pytest.approx(-1.0)  # 255 -> 1, 0 -> -1


def test_encoder_refuses_a_mismatched_backbone(tmp_path):
    (tmp_path / "e.onnx").write_bytes(b"")
    (tmp_path / "e.json").write_text(json.dumps({"model": "a", "pretrained": "b", **CFG}))
    with pytest.raises(RuntimeError, match="built with"):
        Encoder(backbone=("x", "y"), path=tmp_path / "e.onnx")


@pytest.mark.skipif(not (DATA / "encoder.onnx").exists(), reason="export the encoder first")
def test_onnx_matches_open_clip_on_a_real_photo():
    torch = pytest.importorskip("torch")
    from pipeline.build_index import load_model

    enc = Encoder(path=DATA / "encoder.onnx")
    data = FIXTURE.read_bytes()
    model, transform, _, _ = load_model(enc.cfg["model"], enc.cfg["pretrained"])
    with torch.no_grad():
        want = model.encode_image(transform(Image.open(io.BytesIO(data)).convert("RGB")).unsqueeze(0)).numpy()[0]
    want /= np.linalg.norm(want)
    assert float(enc.encode(data) @ want) > 0.9999
