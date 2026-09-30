"""data/nodes.json + data/img -> data/index.npz (CLIP vectors) + data/graph.json (layout + edges)."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from pipeline.filter_nodes import load_merge

DATA = Path(__file__).resolve().parent.parent / "data"
IMG_DIR = DATA / "img"
MODEL, PRETRAINED = "ViT-B-32", "laion2b_s34b_b79k"
MIN_IMAGES = 3  # below this the image centroid is too noisy; fall back to the text vector


def normalize(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-8)


def centroids(image_vecs: np.ndarray, owner: list[str], slugs: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Mean unit vector per slug (zeros when it has no images) and the per-slug image counts."""
    idx = defaultdict(list)
    for i, s in enumerate(owner):
        idx[s].append(i)
    counts = np.array([len(idx[s]) for s in slugs])
    cents = np.zeros((len(slugs), image_vecs.shape[1]) if len(image_vecs) else (len(slugs), 512), dtype=np.float32)
    for j, s in enumerate(slugs):
        if idx[s]:
            cents[j] = normalize(image_vecs[idx[s]].mean(0))
    return cents, counts


def layout(vectors: np.ndarray, seed: int = 0) -> np.ndarray:
    import umap  # slow import, keep it out of the test path for the pure functions

    n = len(vectors)
    if n < 5:  # umap needs neighbours; tiny inputs (tests, smoke runs) get a circle
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return np.stack([np.cos(t), np.sin(t)], 1).astype(np.float32)
    xy = umap.UMAP(n_neighbors=min(15, n - 1), min_dist=0.1, metric="cosine", random_state=seed).fit_transform(vectors)
    return ((xy - xy.mean(0)) / xy.std(0)).astype(np.float32)


def build_graph(nodes: list[dict], xy: np.ndarray, counts: np.ndarray) -> dict:
    slugs = {n["slug"] for n in nodes}
    return {
        "nodes": [{"slug": n["slug"], "name": n["name"], "x": float(x), "y": float(y), "image_count": int(c),
                   "description": n["description"], "other_names": n["other_names"], "key_values": n["key_values"],
                   "wiki_url": n["wiki_url"]} for n, (x, y), c in zip(nodes, xy, counts)],
        "edges": [{"source": n["slug"], "target": t, "type": kind}
                  for n in nodes for kind, field in (("related", "related"), ("subgenre", "subgenres"))
                  for t in n[field] if t in slugs],
    }


def prior(nodes: list[dict]) -> np.ndarray:
    """How well known each aesthetic is, scaled to [0, 1]. Google autocomplete hits dominate;
    wiki mentions break ties (they favour old subcultures over 2020s microtrends)."""
    raw = np.array([2 * np.log1p(n.get("popularity") or 0) + np.log1p(n.get("mentions", 0)) for n in nodes], np.float32)
    return (raw - raw.min()) / max(raw.max() - raw.min(), 1e-6)


def load_model():
    import open_clip
    import torch

    model, _, preprocess = open_clip.create_model_and_transforms(MODEL, pretrained=PRETRAINED)
    model.eval()
    return model, preprocess, open_clip.get_tokenizer(MODEL), torch


def embed_images(paths: list[Path], batch: int = 32) -> np.ndarray:
    from PIL import Image

    model, preprocess, _, torch = load_model()
    out = []
    with torch.no_grad():
        for i in range(0, len(paths), batch):
            imgs = torch.stack([preprocess(Image.open(p).convert("RGB")) for p in paths[i : i + batch]])
            out.append(model.encode_image(imgs).float().numpy())
            print(f"  embedded {min(i + batch, len(paths))}/{len(paths)} images", end="\r")
    print()
    return normalize(np.concatenate(out)) if out else np.zeros((0, 512), np.float32)


def embed_texts(texts: list[str]) -> np.ndarray:
    model, _, tokenizer, torch = load_model()
    with torch.no_grad():
        return normalize(model.encode_text(tokenizer(texts)).float().numpy())


def main(limit: int | None):
    nodes = json.loads((DATA / "nodes.json").read_text())[:limit]
    slugs = [n["slug"] for n in nodes]
    parent_of = load_merge()  # image folders of merged-away children count toward the parent
    paths, owner = [], []
    for folder in sorted(IMG_DIR.iterdir()) if IMG_DIR.exists() else []:
        slug = parent_of.get(folder.name, folder.name)
        if slug in slugs:
            for p in sorted(folder.glob("*.jpg")):
                paths.append(p)
                owner.append(slug)
    print(f"{len(nodes)} nodes, {len(paths)} images")
    image_vecs = embed_images(paths)
    cents, counts = centroids(image_vecs, owner, slugs)
    text_vecs = embed_texts([f"{n['name']} aesthetic. {n['description'][:300]}" for n in nodes])
    # CLIP vectors share a large common component, so generic "photo of a person" aesthetics
    # become hubs that are near everything. Centering on the dataset mean removes it.
    mean_img, mean_txt = cents[counts > 0].mean(0), text_vecs.mean(0)
    # ponytail: text vectors sit in a different region of CLIP space than image centroids, so
    # text-only nodes land in their own UMAP cluster; fine while they're rare after the fetch.
    node_vecs = np.where((counts >= MIN_IMAGES)[:, None], normalize(cents - mean_img), normalize(text_vecs - mean_txt))
    xy = layout(node_vecs)
    np.savez(DATA / "index.npz", slugs=np.array(slugs), centroids=cents, text_vecs=text_vecs, counts=counts, xy=xy,
             mean_img=mean_img, mean_txt=mean_txt, prior=prior(nodes))
    np.savez(DATA / "image_vecs.npz", vecs=image_vecs, owner=np.array(owner))  # for pipeline/evaluate.py
    (DATA / "graph.json").write_text(json.dumps(build_graph(nodes, xy, counts), ensure_ascii=False))
    print(f"wrote data/index.npz and data/graph.json; {int((counts < MIN_IMAGES).sum())} nodes fell back to text vectors")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only the first N nodes (smoke run)")
    main(ap.parse_args().limit)
