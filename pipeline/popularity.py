"""Google autocomplete via serper.dev as a "do people search for this" signal -> data/popularity.json.

Score = number of suggestions for "<name> aesthetic" that contain the aesthetic's full name.
Wiki mentions measure how much the wiki talks about a page; this measures the outside world.
"""
import argparse
import json
import re
from pathlib import Path

import httpx

from pipeline.fetch_images import api_key

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "popularity.json"
RAW = DATA / "popularity_suggestions.json"  # kept so scores can be recomputed without re-querying
SERPER = "https://google.serper.dev/autocomplete"


def plain(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def score(name: str, suggestions: list[str]) -> int:
    """Google suggests "hip hop aesthetic" for "Hip-Hop", so compare with punctuation stripped."""
    return sum(plain(name) in plain(s) for s in suggestions)


def fetch(client: httpx.Client, name: str, key: str) -> list[str]:
    r = client.post(SERPER, headers={"X-API-KEY": key}, json={"q": f"{name} aesthetic"})
    r.raise_for_status()
    return [s.get("value", "") for s in r.json().get("suggestions", [])]


def main(limit: int | None):
    key = api_key()
    nodes = json.loads((DATA / "nodes.json").read_text())
    scores = json.loads(OUT.read_text()) if OUT.exists() else {}
    raw = json.loads(RAW.read_text()) if RAW.exists() else {}
    todo = [n for n in nodes if n["slug"] not in scores or (n["slug"] not in raw and plain(n["name"]) != n["name"].lower())][:limit]
    print(f"{len(todo)} to query ({len(scores)} cached)")
    with httpx.Client(timeout=20) as client:
        for i, n in enumerate(todo, 1):
            raw[n["slug"]] = fetch(client, n["name"], key)
            scores[n["slug"]] = score(n["name"], raw[n["slug"]])
            OUT.write_text(json.dumps(scores, indent=0, sort_keys=True))
            RAW.write_text(json.dumps(raw, indent=0, sort_keys=True))
            print(f"[{i}/{len(todo)}] {n['name']}: {scores[n['slug']]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    main(ap.parse_args().limit)
