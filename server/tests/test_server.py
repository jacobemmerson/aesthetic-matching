import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from server import app as app_mod
from server.match import Index, normalize, overall

# three synthetic aesthetics on orthogonal axes; "text-only" has no images
INDEX = Index(
    slugs=["red", "green", "text-only"],
    centroids=np.array([[1, 0, 0], [0, 1, 0], [0, 0, 0]], dtype=np.float32),
    text_vecs=np.array([[0.9, 0.1, 0], [0.1, 0.9, 0], [0, 0, 1]], dtype=np.float32),
    counts=np.array([5, 5, 0]),
    xy=np.array([[0, 0], [10, 0], [0, 10]], dtype=np.float32),
)


class FakeEncoder:
    def encode(self, data: bytes) -> np.ndarray:
        img = Image.open(io.BytesIO(data)).convert("RGB")  # still rejects junk like the real one
        r, g, _ = img.resize((1, 1)).getpixel((0, 0))
        v = np.array([r, g, 1], dtype=np.float32)
        return v / np.linalg.norm(v)


def jpeg(color: str) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buf, "JPEG")
    return buf.getvalue()


def test_match_and_placement():
    m = INDEX.match(np.array([1, 0, 0], dtype=np.float32))
    assert m["matches"][0]["slug"] == "red" and m["matches"][-1]["slug"] == "text-only"
    assert 0 <= m["x"] <= 10 and 0 <= m["y"] <= 10  # inside the triangle of its matches


def test_overall_represents_every_photo_then_sums():
    res = [{"matches": [{"slug": "a", "score": 0.5}, {"slug": "b", "score": 0.4}]},
           {"matches": [{"slug": "b", "score": 0.5}, {"slug": "a", "score": 0.1}]}]
    assert [m["slug"] for m in overall(res)] == ["b", "a"]
    cluster = [{"matches": [{"slug": "v", "score": 0.4}, {"slug": "v2", "score": 0.4}, {"slug": "v3", "score": 0.39}]},
               {"matches": [{"slug": "c", "score": 0.3}, {"slug": "c2", "score": 0.2}]}]
    assert [m["slug"] for m in overall(cluster)] == ["v", "c", "v2"]


@pytest.fixture
def client(monkeypatch):
    app_mod.state.update(index=INDEX, encoder=FakeEncoder(),
                         graph={"nodes": [], "edges": []},
                         nodes={s: {"name": s.title(), "description": "d", "key_values": ""} for s in INDEX.slugs})
    app_mod.hits.clear()
    monkeypatch.setattr(app_mod.app.router, "on_startup", [])
    return TestClient(app_mod.app)


def test_analyze_happy_path(client):
    r = client.post("/api/analyze", files=[("images", ("a.jpg", jpeg("red"), "image/jpeg")), ("images", ("b.jpg", jpeg("green"), "image/jpeg"))])
    assert r.status_code == 200, r.text
    body = r.json()
    assert [i["matches"][0]["slug"] for i in body["images"]] == ["red", "green"]
    assert body["overall"][0]["slug"] in {"red", "green"} and "roast" not in body
    assert body["names"]["red"] == "Red"


def test_rejects_junk_and_rate_limits(client):
    assert client.post("/api/analyze", files=[("images", ("x.txt", b"nope", "text/plain"))]).status_code == 400
    for _ in range(app_mod.RATE_LIMIT - 1):  # the junk request above already used one slot
        assert client.post("/api/analyze", files=[("images", ("a.jpg", jpeg("red"), "image/jpeg"))]).status_code == 200
    assert client.post("/api/analyze", files=[("images", ("a.jpg", jpeg("red"), "image/jpeg"))]).status_code == 429


def test_centering_removes_hub():
    # "hub" sits at the dataset mean direction; after centering it should stop winning everything
    cents = np.array([[1, 1, 0.2], [1, 1, -0.2], [1, 1, 0]], dtype=np.float32)
    cents /= np.linalg.norm(cents, axis=1, keepdims=True)
    idx = Index(slugs=["up", "down", "hub"], centroids=cents, text_vecs=cents.copy(), counts=np.array([5, 5, 5]),
                xy=np.zeros((3, 2), np.float32), mean_img=cents.mean(0), mean_txt=cents.mean(0))
    assert idx.match(cents[0])["matches"][0]["slug"] == "up"
    assert idx.match(cents[1])["matches"][0]["slug"] == "down"


def test_prior_breaks_near_ties_toward_known_aesthetics():
    cents = normalize(np.array([[1, 0.05, 0], [1, -0.05, 0]], dtype=np.float32))
    base = dict(centroids=cents, text_vecs=cents.copy(), counts=np.array([5, 5]), xy=np.zeros((2, 2), np.float32))
    query = np.array([1, 0.02, 0], dtype=np.float32)
    assert Index(slugs=["a", "b"], **base).match(query)["matches"][0]["slug"] == "a"
    assert Index(slugs=["a", "b"], prior=np.array([0, 1], np.float32), **base).match(query)["matches"][0]["slug"] == "b"


def test_forged_forwarded_header_does_not_dodge_rate_limit(client):
    for i in range(app_mod.RATE_LIMIT):
        assert client.post("/api/analyze", headers={"x-forwarded-for": f"10.0.0.{i}"},
                           files=[("images", ("a.jpg", jpeg("red"), "image/jpeg"))]).status_code == 200
    assert client.post("/api/analyze", headers={"x-forwarded-for": "10.0.0.99"},
                       files=[("images", ("a.jpg", jpeg("red"), "image/jpeg"))]).status_code == 429
