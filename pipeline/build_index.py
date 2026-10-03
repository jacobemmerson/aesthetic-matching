"""data/nodes.json + data/img -> data/index.npz (CLIP vectors) + data/graph.json (layout + edges)."""
import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import numpy as np

from pipeline.filter_nodes import load_merge

DATA = Path(__file__).resolve().parent.parent / "data"
IMG_DIR = DATA / "img"
# Backbone for every embedding in a build; the index records it so the server loads the same one.
# Override with CLIP_MODEL / CLIP_PRETRAINED when building a tagged index with another backbone.
MODEL = os.environ.get("CLIP_MODEL", "ViT-B-32")
PRETRAINED = os.environ.get("CLIP_PRETRAINED", "laion2b_s34b_b79k")
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

    """Unit vectors on a sphere: UMAP embeds straight into (latitude, longitude) so the map has no
    edges to pan off."""
    n = len(vectors)
    if n < 5:  # umap needs neighbours; tiny inputs (tests, smoke runs) sit on the equator
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return np.stack([np.cos(t), np.sin(t), np.zeros(n)], 1).astype(np.float32)
    lat, lon = umap.UMAP(n_neighbors=min(15, n - 1), min_dist=0.1, metric="cosine", output_metric="haversine",
                         random_state=seed).fit_transform(vectors).T
    return np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], 1).astype(np.float32)


def build_graph(nodes: list[dict], xyz: np.ndarray, counts: np.ndarray, ratings: dict[str, float] | None = None) -> dict:
    """`ratings`: the judges' plain mainstream rating per slug (data/mainstream.json), served as the basic score."""
    slugs = {n["slug"] for n in nodes}
    ratings = ratings or {}
    return {
        "nodes": [{"slug": n["slug"], "name": n["name"], "x": float(x), "y": float(y), "z": float(z), "image_count": int(c),
                   "description": n["description"], "other_names": n["other_names"], "key_values": n["key_values"],
                   "wiki_url": n["wiki_url"], "mainstream": ratings.get(n["slug"])} for n, (x, y, z), c in zip(nodes, xyz, counts)],
        "edges": [{"source": n["slug"], "target": t, "type": kind}
                  for n in nodes for kind, field in (("related", "related"), ("subgenre", "subgenres"))
                  for t in n[field] if t in slugs],
    }


def prior(nodes: list[dict]) -> np.ndarray:
    """How well known each aesthetic is, scaled to [0, 1]. Google autocomplete hits dominate;
    wiki mentions break ties (they favour old subcultures over 2020s microtrends)."""
    raw = np.array([2 * np.log1p(n.get("popularity") or 0) + np.log1p(n.get("mentions", 0)) for n in nodes], np.float32)
    return (raw - raw.min()) / max(raw.max() - raw.min(), 1e-6)


def load_model(name: str = MODEL, pretrained: str = PRETRAINED):
    import open_clip
    import torch

    model, _, preprocess = open_clip.create_model_and_transforms(name, pretrained=pretrained)
    model.eval()
    return model, preprocess, open_clip.get_tokenizer(name), torch


def random_crop(img, rng):
    fw, fh = rng.uniform(0.5, 0.9, 2)
    w, h = int(img.width * fw), int(img.height * fh)
    x, y = rng.integers(0, img.width - w + 1), rng.integers(0, img.height - h + 1)
    return img.crop((x, y, x + w, y + h))


def embed_images(paths: list[Path], batch: int = 32, crops: int = 0, masker=None, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Unit vectors for each path, then `crops` random crops per path. `source` maps every row
    back to its path index so crops stay with their image in CV folds and attribute labels."""
    from PIL import Image

    model, preprocess, _, torch = load_model()
    rng = np.random.default_rng(seed)

    def load(p):
        img = Image.open(p).convert("RGB")
        return masker.mask(img) if masker else img

    jobs = [(i, lambda p=p: load(p)) for i, p in enumerate(paths)]
    jobs += [(i, lambda p=p: random_crop(load(p), rng)) for _ in range(crops) for i, p in enumerate(paths)]
    out = []
    with torch.no_grad():
        for i in range(0, len(jobs), batch):
            imgs = torch.stack([preprocess(job()) for _, job in jobs[i : i + batch]])
            out.append(model.encode_image(imgs).float().numpy())
            print(f"  embedded {min(i + batch, len(jobs))}/{len(jobs)} images", end="\r")
    print()
    source = np.array([i for i, _ in jobs], dtype=np.int64)
    return (normalize(np.concatenate(out)) if out else np.zeros((0, 512), np.float32)), source


def embed_texts(texts: list[str]) -> np.ndarray:
    model, _, tokenizer, torch = load_model()
    with torch.no_grad():
        return normalize(model.encode_text(tokenizer(texts)).float().numpy())


def main(limit: int | None, crops: int = 0, mask_faces: bool = False, tag: str = "", debias: str = "none", head: str = "none",
         prune: bool = True):
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
    masker = None
    if mask_faces or prune:
        from pipeline.faces import Detector

        masker = Detector()
    if prune:  # portraits encode who was photographed, not the aesthetic
        from PIL import Image

        from pipeline.prune import MAX_FACE_FRACTION, face_fraction

        keep = [face_fraction(masker.boxes(im := Image.open(p).convert("RGB")), im.width, im.height) <= MAX_FACE_FRACTION for p in paths]
        print(f"pruned {len(paths) - sum(keep)} portrait images")
        paths, owner = [p for p, k in zip(paths, keep) if k], [o for o, k in zip(owner, keep) if k]
    image_vecs, source = embed_images(paths, crops=crops, masker=masker if mask_faces else None)
    owner = [owner[i] for i in source]
    if prune:
        from pipeline.prune import near_duplicates

        dup = near_duplicates(image_vecs, owner)
        print(f"pruned {int(dup.sum())} near-duplicate images")
        image_vecs, source, owner = image_vecs[~dup], source[~dup], [o for o, d in zip(owner, dup) if not d]
    cents, counts = centroids(image_vecs, owner, slugs)
    text_vecs = embed_texts([f"{n['name']} aesthetic. {n['description'][:300]}" for n in nodes])
    # CLIP vectors share a large common component, so generic "photo of a person" aesthetics
    # become hubs that are near everything. Centering on the dataset mean removes it.
    mean_img, mean_txt = cents[counts > 0].mean(0), text_vecs.mean(0)
    # ponytail: text vectors sit in a different region of CLIP space than image centroids, so
    # text-only nodes land in their own UMAP cluster; fine while they're rare after the fetch.
    node_vecs = np.where((counts >= MIN_IMAGES)[:, None], normalize(cents - mean_img), normalize(text_vecs - mean_txt))
    xyz = layout(node_vecs)
    extra = {}
    if debias != "none":
        t = np.load(DATA / f"debias_{debias}{'_masked' if mask_faces and debias == 'leace' else ''}.npz")
        extra = {"proj_P": t["P"], "proj_b": t["b"]}
    if head != "none":
        from pipeline.debias import apply
        from pipeline.train_head import best_l2, group_weights, train

        owner_idx = np.array([slugs.index(o) for o in owner])
        treated = apply(image_vecs, extra["proj_P"], extra["proj_b"]) if extra else image_vecs  # scores() projects the query first
        weights = group_weights(np.load(DATA / "reference_attrs.npz")["race"][source], owner_idx) if head == "reweighted" else None
        l2 = best_l2(treated, owner_idx, len(slugs), source, weights)
        extra["head_w"], extra["head_b"] = train(treated, owner_idx, len(slugs), weights, l2)
        print(f"head: l2={l2}")
    suffix = f"_{tag}" if tag else ""
    np.savez(DATA / f"index{suffix}.npz", slugs=np.array(slugs), centroids=cents, text_vecs=text_vecs, counts=counts, xyz=xyz,
             mean_img=mean_img, mean_txt=mean_txt, prior=prior(nodes), masked_faces=np.array(mask_faces),
             model=np.array(MODEL), pretrained=np.array(PRETRAINED), **extra)
    np.savez(DATA / f"image_vecs{suffix}.npz", vecs=image_vecs, owner=np.array(owner),  # for evaluate/fairness/probe
             path=np.array([str(paths[i]) for i in source]), source=source)
    if not tag:
        ratings = {s: v["mainstream"] for s, v in json.loads((DATA / "mainstream.json").read_text()).items()}
        (DATA / "graph.json").write_text(json.dumps(build_graph(nodes, xyz, counts, ratings), ensure_ascii=False))
    print(f"wrote data/index{suffix}.npz; {int((counts < MIN_IMAGES).sum())} nodes fell back to text vectors")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only the first N nodes (smoke run)")
    ap.add_argument("--crops", type=int, default=0, help="extra random crops embedded per image")
    ap.add_argument("--mask-faces", action="store_true", help="blank detected faces before embedding")
    ap.add_argument("--tag", default="", help="write index_TAG.npz / image_vecs_TAG.npz and skip graph.json")
    ap.add_argument("--debias", choices=["none", "prompt", "leace"], default="none", help="store this debias map in the index")
    ap.add_argument("--head", choices=["none", "plain", "reweighted"], default="none", help="train a linear head into the index")
    ap.add_argument("--no-prune", action="store_true", help="keep portrait and near-duplicate reference images")
    a = ap.parse_args()
    main(a.limit, a.crops, a.mask_faces, a.tag, a.debias, a.head, prune=not a.no_prune)
