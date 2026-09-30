"""Pull reference images per aesthetic from Google Images via serper.dev (resumable).

Images are only used to build embeddings; they are never redistributed or shown, so results
are deliberately unfiltered by licence (Google's CC filter is ignored/poor anyway).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

import httpx
from PIL import Image

DATA = Path(__file__).resolve().parent.parent / "data"
IMAGES = DATA / "images.jsonl"
IMG_DIR = DATA / "img"
SERPER = "https://google.serper.dev/images"
MAX_BYTES = 5_000_000
MAX_SIDE = 512


class QuotaExhausted(Exception):
    pass


def search(client: httpx.Client, node: dict, num: int, key: str) -> list[dict]:
    rows = []
    for phrasing in (f"{node['name']} aesthetic", f"{node['name']} style"):  # some queries come back empty; retry once reworded
        for attempt in range(3):
            try:
                r = client.post(SERPER, headers={"X-API-KEY": key}, json={"q": phrasing, "num": num})
                break
            except httpx.TransportError:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        if r.status_code in (400, 401, 402, 403, 429):
            raise QuotaExhausted(r.text[:200])
        r.raise_for_status()
        rows = [{"slug": node["slug"], "url": it["imageUrl"], "page_url": it.get("link", ""), "title": it.get("title", "")}
                for it in r.json().get("images", [])]
        if rows:
            return rows
    return rows


def download(client: httpx.Client, url: str, dest: Path) -> bool:
    try:
        r = client.get(url, timeout=10, follow_redirects=True)
        if r.status_code != 200 or len(r.content) > MAX_BYTES:
            return False
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return False
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=88)
    return True


def done_slugs(path: Path) -> set[str]:
    return {json.loads(l)["slug"] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()


def api_key() -> str:
    env = dict(os.environ)
    dotenv = DATA.parent / ".env"
    if dotenv.exists():
        env.update(l.split("=", 1) for l in dotenv.read_text().splitlines() if "=" in l and not l.startswith("#"))
    key = env.get("SERPER_API_KEY", "").strip()
    return key or sys.exit("set SERPER_API_KEY in the environment or in .env")


def main(limit: int | None, num: int):
    key = api_key()
    nodes = json.loads((DATA / "nodes.json").read_text())
    done = done_slugs(IMAGES)
    todo = [n for n in nodes if n["slug"] not in done][:limit]
    print(f"{len(todo)} aesthetics to fetch this run ({len(done)} already done, {len(nodes)} total)")
    ua = {"User-Agent": "Mozilla/5.0 (compatible; aesthetics-roast-app/0.1)"}
    with httpx.Client(headers=ua, timeout=20) as client, IMAGES.open("a") as out:
        for i, node in enumerate(todo, 1):
            try:
                rows = search(client, node, num, key)
            except QuotaExhausted as e:
                print(f"quota exhausted after {i - 1} aesthetics ({e}); rerun later to resume")
                return
            rows = list({hashlib.sha1(r["url"].encode()).hexdigest()[:12]: r for r in rows}.items())  # dedupe by url
            with ThreadPoolExecutor(8) as pool:
                flags = pool.map(lambda dr: download(client, dr[1]["url"], IMG_DIR / node["slug"] / f"{dr[0]}.jpg"), rows)
            saved = 0
            for (_, row), row["saved"] in zip(rows, flags):
                saved += row["saved"]
                out.write(json.dumps(row, ensure_ascii=False) + "\n")  # every row, so a slug counts as done even if all downloads failed
            out.flush()
            print(f"[{i}/{len(todo)}] {node['name']}: {saved}/{len(rows)} images")
            time.sleep(0.5)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only the first N not-yet-fetched aesthetics (smoke run)")
    ap.add_argument("--num", type=int, default=20, help="images requested per aesthetic")
    a = ap.parse_args()
    main(a.limit, a.num)
