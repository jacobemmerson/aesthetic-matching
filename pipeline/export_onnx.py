"""open_clip image tower -> data/encoder.onnx + data/encoder.json, so the server embeds photos with onnxruntime and no torch."""
import argparse
import json
from pathlib import Path

import numpy as np

from pipeline.build_index import DATA, MODEL, PRETRAINED, load_model

OUT = DATA / "encoder.onnx"


def export(name: str = MODEL, pretrained: str = PRETRAINED, out: Path = OUT) -> Path:
    model, _, _, torch = load_model(name, pretrained)
    cfg = model.visual.preprocess_cfg
    h, w = cfg["size"] if isinstance(cfg["size"], (tuple, list)) else (cfg["size"], cfg["size"])

    class Tower(torch.nn.Module):  # encode_image, not just the visual trunk: it includes the projection the index was built with
        def forward(self, image):
            return model.encode_image(image)

    sample = torch.zeros(1, 3, h, w)
    torch.onnx.export(Tower().eval(), (sample,), str(out), input_names=["image"], output_names=["embedding"],
                      dynamic_shapes={"image": {0: torch.export.Dim("batch")}}, opset_version=18, external_data=False)  # one self-contained file
    out.with_suffix(".json").write_text(json.dumps({
        "model": name, "pretrained": pretrained, "size": [h, w], "mean": list(cfg["mean"]), "std": list(cfg["std"]),
        "interpolation": cfg["interpolation"], "resize_mode": cfg["resize_mode"],
    }, indent=1))
    with torch.no_grad():
        want = model.encode_image(sample).numpy()
    return out, want


def check(out: Path, sample_out: np.ndarray) -> float:
    import onnxruntime as ort

    session = ort.InferenceSession(str(out), providers=["CPUExecutionProvider"])
    h, w = json.loads(out.with_suffix(".json").read_text())["size"]
    got = session.run(None, {"image": np.zeros((1, 3, h, w), np.float32)})[0]
    return float(np.abs(got - sample_out).max())


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default=MODEL)
    p.add_argument("--pretrained", default=PRETRAINED)
    p.add_argument("--out", type=Path, default=OUT)
    a = p.parse_args()
    out, want = export(a.model, a.pretrained, a.out)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.0f} MB); max |onnx - torch| on a blank image: {check(out, want):.2e}")
