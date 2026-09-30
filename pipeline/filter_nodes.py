"""data/wiki.json -> data/nodes.json, minus the deny list and unusable pages."""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
EXCLUDE = Path(__file__).resolve().parent / "exclude.txt"
MERGE = Path(__file__).resolve().parent / "merge.txt"
MIN_DESCRIPTION = 150
RAW = DATA / "raw"


def mention_counts(nodes: list[dict]) -> Counter:
    """How many other wiki pages link to each aesthetic anywhere in their body text.

    A popularity proxy: infobox degree only measures how mature a wiki page is, so new but
    famous aesthetics (Brat Summer, Mob Wife) have few edges but many mentions.
    """
    title2slug = {n["title"].lower(): n["slug"] for n in nodes}
    for n in nodes:
        for alias in filter(None, (a.strip() for a in n["other_names"].split(","))):
            title2slug.setdefault(alias.lower(), n["slug"])
    counts = Counter()
    for page in RAW.glob("*.txt"):
        for target in set(re.findall(r"\[\[([^\]|#]+)", page.read_text())):
            slug = title2slug.get(target.replace("_", " ").strip().lower())
            if slug and slug != page.stem:
                counts[slug] += 1
    return counts


def load_exclude() -> set[str]:
    lines = EXCLUDE.read_text().splitlines() if EXCLUDE.exists() else []
    return {l.split("#")[0].strip() for l in lines if l.split("#")[0].strip()}


def load_merge() -> dict[str, str]:
    lines = MERGE.read_text().splitlines() if MERGE.exists() else []
    pairs = [l.split("#")[0].split("->") for l in lines if "->" in l.split("#")[0]]
    return {child.strip(): parent.strip() for child, parent in pairs}


def merge_nodes(nodes: list[dict], merge: dict[str, str]) -> list[dict]:
    """Fold each child into its parent: edges re-point, names become aliases, mentions add up."""
    by = {n["slug"]: n for n in nodes}
    missing = [c for c in merge if c not in by] + [p for p in merge.values() if p not in by]
    if missing:
        raise SystemExit(f"merge.txt names unknown slugs: {missing}")
    for child, parent in merge.items():
        by[parent]["other_names"] = ", ".join(filter(None, [by[parent]["other_names"], by[child]["name"], by[child]["other_names"]]))
        by[parent]["mentions"] = by[parent].get("mentions", 0) + by[child].get("mentions", 0)
        for field in ("related", "subgenres"):
            by[parent][field] = by[parent][field] + by[child][field]
    kept = [n for n in nodes if n["slug"] not in merge]
    for n in kept:
        for field in ("related", "subgenres"):
            n[field] = sorted({merge.get(s, s) for s in n[field]} - {n["slug"]})
    return kept


def filter_nodes(nodes: list[dict], exclude: set[str], mentions: Counter | None = None, min_mentions: int = 0,
                 popularity: dict[str, int] | None = None, min_popularity: int = 0) -> tuple[list[dict], dict[str, str]]:
    mentions = mentions or Counter()
    popularity = popularity or {}
    degree = Counter()
    for n in nodes:
        degree[n["slug"]] += len(n["related"]) + len(n["subgenres"])
        degree.update(n["related"] + n["subgenres"])
    dropped = {}
    for n in nodes:
        if n["slug"] in exclude:
            dropped[n["slug"]] = "in exclude.txt"
        elif len(n["description"]) < MIN_DESCRIPTION:
            dropped[n["slug"]] = f"description < {MIN_DESCRIPTION} chars"
        elif degree[n["slug"]] == 0:
            dropped[n["slug"]] = "no edges"
        elif mentions[n["slug"]] < min_mentions:
            dropped[n["slug"]] = f"mentioned by < {min_mentions} pages"
        elif n["slug"] in popularity and popularity[n["slug"]] < min_popularity:
            dropped[n["slug"]] = f"< {min_popularity} google autocomplete hits"
    kept = [n for n in nodes if n["slug"] not in dropped]
    for n in kept:
        n["mentions"] = mentions[n["slug"]]
        n["popularity"] = popularity.get(n["slug"])
        for field in ("related", "subgenres"):
            n[field] = [s for s in n[field] if s not in dropped]
    return kept, dropped


def write_review_page(kept: list[dict], dropped: dict[str, str]) -> None:
    """Single-file HTML table with checkboxes; 'copy' button emits lines for exclude.txt."""
    degree = Counter()
    for n in kept:
        degree[n["slug"]] += len(n["related"]) + len(n["subgenres"])
        degree.update(n["related"] + n["subgenres"])
    rows = [
        {"slug": n["slug"], "name": n["name"], "degree": degree[n["slug"]], "mentions": n["mentions"], "pop": n.get("popularity"), "words": n["word_count"],
         "desc": n["description"][:260], "url": n["wiki_url"], "infobox": n["has_infobox"]}
        for n in kept
    ]
    html = """<!doctype html><meta charset=utf-8><title>Aesthetics review</title>
<style>body{font:14px system-ui;margin:16px}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:4px 6px;vertical-align:top;text-align:left}
th{cursor:pointer;position:sticky;top:0;background:#fff}.d{color:#555;font-size:13px}button{margin-left:8px}input[type=search]{width:20em}</style>
<p><input type=search id=q placeholder="filter by name or description"> <span id=n></span>
<button onclick="copy()">copy checked slugs for exclude.txt</button> <span id=msg></span></p>
<table id=t><thead><tr><th></th><th data-k=name>name</th><th data-k=degree>edges</th><th data-k=mentions>mentions</th><th data-k=pop>google</th><th data-k=words>words</th><th>description</th></tr></thead><tbody></tbody></table>
<h3>Already dropped by rules</h3><pre id=dropped></pre>
<script>
const rows=__ROWS__, dropped=__DROPPED__, checked=new Set(JSON.parse(localStorage.getItem('exclude')||'[]'));
let key='name',asc=true;
function render(){const q=q_.value.toLowerCase();const rs=rows.filter(r=>(r.name+' '+r.desc).toLowerCase().includes(q))
 .sort((a,b)=>(a[key]>b[key]?1:-1)*(asc?1:-1));n.textContent=rs.length+' of '+rows.length;
 t.tBodies[0].innerHTML=rs.map(r=>`<tr><td><input type=checkbox data-s="${r.slug}" ${checked.has(r.slug)?'checked':''}></td>
 <td><a href="${r.url}" target=_blank>${r.name}</a>${r.infobox?'':' <small>(no infobox)</small>'}</td><td>${r.degree}</td><td>${r.mentions}</td><td>${r.pop ?? ''}</td><td>${r.words}</td><td class=d>${r.desc}</td></tr>`).join('')}
const q_=document.getElementById('q');q_.oninput=render;
t.tBodies[0].onchange=e=>{const s=e.target.dataset.s;e.target.checked?checked.add(s):checked.delete(s);localStorage.setItem('exclude',JSON.stringify([...checked]))};
document.querySelectorAll('th[data-k]').forEach(h=>h.onclick=()=>{asc=key===h.dataset.k?!asc:true;key=h.dataset.k;render()});
function copy(){navigator.clipboard.writeText([...checked].sort().join('\\n')+'\\n');msg.textContent=checked.size+' slugs copied'}
document.getElementById('dropped').textContent=Object.entries(dropped).map(([s,w])=>s.padEnd(36)+w).join('\\n');render();
</script>"""
    html = html.replace("__ROWS__", json.dumps(rows, ensure_ascii=False)).replace("__DROPPED__", json.dumps(dropped))
    (DATA / "review.html").write_text(html)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-mentions", type=int, default=8, help="drop aesthetics linked from fewer body texts")
    ap.add_argument("--min-popularity", type=int, default=3, help="drop aesthetics with fewer google autocomplete hits (needs data/popularity.json)")
    args = ap.parse_args()
    pop_file = DATA / "popularity.json"
    popularity = json.loads(pop_file.read_text()) if pop_file.exists() else {}
    nodes = json.loads((DATA / "wiki.json").read_text())
    mentions = mention_counts(nodes)
    for n in nodes:
        n["mentions"] = mentions[n["slug"]]
        n["popularity"] = popularity.get(n["slug"])
    nodes = merge_nodes(nodes, load_merge())
    kept, dropped = filter_nodes(nodes, load_exclude(), Counter({n["slug"]: n["mentions"] for n in nodes}), args.min_mentions,
                                 popularity, args.min_popularity)
    (DATA / "nodes.json").write_text(json.dumps(kept, indent=1, ensure_ascii=False))
    for slug, why in sorted(dropped.items(), key=lambda kv: kv[1]):
        print(f"drop {slug:40} {why}")
    write_review_page(kept, dropped)
    print(f"{len(kept)} kept, {len(dropped)} dropped -> data/nodes.json (review at data/review.html)")
