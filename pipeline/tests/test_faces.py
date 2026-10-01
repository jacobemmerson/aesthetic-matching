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
