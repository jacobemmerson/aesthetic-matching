import json

import httpx

from pipeline import fetch_images as fi

SERPER_PAGE = {"images": [{"imageUrl": "https://x.test/a.jpg", "link": "https://x.test/a", "title": "A"},
                          {"imageUrl": "https://x.test/b.jpg", "link": "https://x.test/b", "title": "B"}]}


def test_search_rows():
    calls = []

    def handler(request):
        calls.append((request.headers.get("X-API-KEY"), json.loads(request.content)))
        return httpx.Response(200, json=SERPER_PAGE)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    rows = fi.search(client, {"slug": "cottagecore", "name": "Cottagecore"}, num=20, key="k")
    assert rows[0] == {"slug": "cottagecore", "url": "https://x.test/a.jpg", "page_url": "https://x.test/a", "title": "A"}
    assert len(rows) == 2 and calls == [("k", {"q": "Cottagecore aesthetic", "num": 20})]


def test_quota_exhausted_raises():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(429, text="Not enough credits")))
    try:
        fi.search(client, {"slug": "x", "name": "X"}, num=10, key="k")
    except fi.QuotaExhausted:
        return
    assert False, "expected QuotaExhausted"


def test_download_resizes_and_rejects_junk(tmp_path):
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.new("RGB", (1600, 800), "red").save(buf, "JPEG")

    def handler(request):
        return httpx.Response(200, content=buf.getvalue() if "good" in str(request.url) else b"not an image")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert fi.download(client, "https://x.test/good.jpg", tmp_path / "0.jpg") is True
    assert fi.download(client, "https://x.test/bad.jpg", tmp_path / "1.jpg") is False
    assert Image.open(tmp_path / "0.jpg").size == (512, 256) and not (tmp_path / "1.jpg").exists()


def test_done_slugs(tmp_path):
    f = tmp_path / "images.jsonl"
    f.write_text(json.dumps({"slug": "a", "url": "u"}) + "\n" + json.dumps({"slug": "a", "url": "v"}) + "\n")
    assert fi.done_slugs(f) == {"a"}
