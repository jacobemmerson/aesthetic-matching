"""Scrape every aesthetic page from aesthetics.fandom.com into data/wiki.json."""
import argparse
import json
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path

import httpx
import mwparserfromhell as mw

API = "https://aesthetics.fandom.com/api.php"
HEADERS = {"User-Agent": "aesthetics-roast-app/0.1 (jemmerson@ucsd.edu)"}
DATA = Path(__file__).resolve().parent.parent / "data"
LINK_FIELDS = {"related": "related_aesthetics", "subgenres": "subgenres"}
TEXT_FIELDS = ["other_names", "key_motifs", "key_colours", "key_values", "decade_of_origin"]
MIN_INBOUND_WITHOUT_INFOBOX = 3


def slugify(title: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")


def split_infobox(wikitext: str) -> tuple[dict[str, str], str]:
    """Return ({param: raw value}, wikitext with the infobox removed).

    Done by hand because pages often have unbalanced ''' or <big> inside the infobox,
    which makes mwparserfromhell silently treat the whole template as plain text.
    """
    m = re.search(r"\{\{\s*Aesthetic\s*(?=[|\n])", wikitext)
    if not m:
        return {}, wikitext
    depth, i = 1, m.end()
    while depth and i < len(wikitext):
        if wikitext.startswith("{{", i):
            depth, i = depth + 1, i + 2
        elif wikitext.startswith("}}", i):
            depth, i = depth - 1, i + 2
        else:
            i += 1
    body = wikitext[m.end() : i - 2]
    params = {}
    # split on pipes that start a "key=" pair; pipes inside [[a|b]] links never do
    for chunk in re.split(r"\|(?=\s*[a-z_0-9/]+\s*=)", body)[1:]:
        key, _, value = chunk.partition("=")
        params[key.strip()] = value.strip()
    return params, wikitext[: m.start()] + wikitext[i:]


def link_targets(value: str) -> list[str]:
    return [str(l.title).replace("_", " ").strip() for l in mw.parse(value).filter_wikilinks()]


def lead_text(code) -> str:
    lead = code.get_sections(include_lead=True)[0]
    for node in list(lead.ifilter_templates()) + [
        l for l in lead.ifilter_wikilinks() if str(l.title).lower().startswith(("file:", "image:"))
    ] + [t for t in lead.ifilter_tags() if str(t.tag).lower() == "ref"]:  # footnote bodies, not prose
        try:
            lead.remove(node)
        except ValueError:
            pass
    return re.sub(r"\n{2,}", "\n", lead.strip_code(normalize=True, collapse=True)).strip()


def parse_page(title: str, wikitext: str) -> dict:
    """Parse any page; `has_infobox` tells the caller whether it is a proper aesthetic page."""
    box, rest = split_infobox(wikitext.replace("{{PAGENAME}}", title))
    code = mw.parse(rest)
    page = {
        "name": mw.parse(box.get("title1", "")).strip_code().strip(" |") or title,  # wiki has "title1=Basic Girl|"
        "slug": slugify(title),
        "title": title,
        "wiki_url": "https://aesthetics.fandom.com/wiki/" + title.replace(" ", "_"),
        "has_infobox": bool(box),
        "description": lead_text(code),
        "word_count": len(code.strip_code().split()),
    }
    page.update({f: mw.parse(box.get(f, "")).strip_code(normalize=True).strip() for f in TEXT_FIELDS})
    page.update({k: link_targets(box.get(v, "")) for k, v in LINK_FIELDS.items()})
    return page


def api(client: httpx.Client, **params) -> dict:
    for attempt in range(5):
        r = client.get(API, params={**params, "format": "json", "formatversion": "2"})
        if r.status_code < 429:
            return r.json()
        time.sleep(2**attempt)
    r.raise_for_status()


def all_titles(client: httpx.Client, redirects: bool) -> list[str]:
    titles, cont = [], {}
    while True:
        d = api(client, action="query", list="allpages", apnamespace=0, aplimit=500,
                apfilterredir="redirects" if redirects else "nonredirects", **cont)
        titles += [p["title"] for p in d["query"]["allpages"]]
        if "continue" not in d:
            return titles
        cont = {"apcontinue": d["continue"]["apcontinue"]}


def redirect_map(client: httpx.Client) -> dict[str, str]:
    froms, out = all_titles(client, redirects=True), {}
    for i in range(0, len(froms), 50):
        d = api(client, action="query", titles="|".join(froms[i : i + 50]), redirects=1)
        out.update({r["from"]: r["to"] for r in d["query"].get("redirects", [])})
        time.sleep(0.3)
    return out


def fetch_wikitext(client: httpx.Client, titles: list[str]) -> dict[str, str]:
    """Batch of up to 50 titles -> {title: wikitext}, cached under data/raw."""
    raw = DATA / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    out = {t: (raw / f"{slugify(t)}.txt").read_text() for t in titles if (raw / f"{slugify(t)}.txt").exists()}
    missing = [t for t in titles if t not in out]
    for i in range(0, len(missing), 50):
        d = api(client, action="query", prop="revisions", rvprop="content", rvslots="main", titles="|".join(missing[i : i + 50]))
        for p in d["query"]["pages"]:
            if "revisions" in p:
                text = p["revisions"][0]["slots"]["main"]["content"]
                (raw / f"{slugify(p['title'])}.txt").write_text(text)
                out[p["title"]] = text
        time.sleep(0.3)
    return out


def resolve_links(pages: list[dict], redirects: dict[str, str]) -> Counter:
    """Rewrite link titles to slugs in place; returns inbound-link counts per slug."""
    by_title = {p["title"].lower(): p["slug"] for p in pages}
    inbound = Counter()
    for p in pages:
        for field in LINK_FIELDS:
            targets = [redirects.get(t, t) for t in p[field]]
            p[field] = sorted({s for t in targets if (s := by_title.get(t.lower())) and s != p["slug"]})
            inbound.update(p[field])
    return inbound


def main(limit: int | None):
    with httpx.Client(headers=HEADERS, timeout=30) as client:
        titles = all_titles(client, redirects=False)
        print(f"{len(titles)} non-redirect pages in main namespace")
        redirects = redirect_map(client)
        texts = fetch_wikitext(client, titles[:limit] if limit else titles)
    pages = [parse_page(t, w) for t, w in texts.items()]
    inbound = resolve_links(pages, redirects)
    kept = [p for p in pages if p["has_infobox"] or inbound[p["slug"]] >= MIN_INBOUND_WITHOUT_INFOBOX]
    resolve_links(kept, redirects)  # drop edges into pages we just discarded
    DATA.mkdir(exist_ok=True)
    (DATA / "wiki.json").write_text(json.dumps(kept, indent=1, ensure_ascii=False))
    no_box = sorted((inbound[p["slug"]], p["title"]) for p in kept if not p["has_infobox"])
    print(f"{len(kept)} pages written to data/wiki.json ({len(pages) - len(kept)} dropped for having no infobox and <{MIN_INBOUND_WITHOUT_INFOBOX} inbound links)")
    print("kept without infobox:", ", ".join(f"{t} ({n})" for n, t in no_box))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only fetch the first N titles (smoke run)")
    main(ap.parse_args().limit)
