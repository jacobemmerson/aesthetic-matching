"""Spread the served layout in place: relaxes the node positions in data/index.npz and data/graph.json together
(they must agree, since the server places photos with the index and the client draws the graph)."""
import argparse
import json

import numpy as np

from pipeline.build_index import DATA, RELAX_ITERS, RELAX_STEP, relax


def spacing(xyz: np.ndarray) -> float:
    """Median angle in degrees from each node to its nearest neighbour; 152 evenly spread points would give about 16."""
    P = xyz / np.linalg.norm(xyz, axis=1, keepdims=True)
    D = np.degrees(np.arccos(np.clip(P @ P.T, -1, 1)))
    np.fill_diagonal(D, np.inf)
    return float(np.median(D.min(1)))


def main(iters: int, step: float):
    index = dict(np.load(DATA / "index.npz"))
    graph = json.loads((DATA / "graph.json").read_text())
    before = index["xyz"]
    after = relax(before, iters, step)
    by_slug = dict(zip(index["slugs"].tolist(), after))
    for n in graph["nodes"]:
        n["x"], n["y"], n["z"] = (float(v) for v in by_slug[n["slug"]])
    index["xyz"] = after
    np.savez(DATA / "index.npz", **index)
    (DATA / "graph.json").write_text(json.dumps(graph, ensure_ascii=False))
    print(f"nearest-neighbour spacing: {spacing(before):.1f} deg -> {spacing(after):.1f} deg")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iters", type=int, default=RELAX_ITERS)
    ap.add_argument("--step", type=float, default=RELAX_STEP)
    a = ap.parse_args()
    main(a.iters, a.step)
