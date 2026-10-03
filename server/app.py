import json
import os
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from server.match import Encoder, Index, aggregate, basic_score, cover

DATA = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
WEB = Path(__file__).resolve().parent.parent / "web" / "dist"
MIN_IMAGES, MAX_IMAGES, MAX_BYTES = 3, 10, 5_000_000
RATE_LIMIT, RATE_WINDOW = 5, 3600  # analyses per IP per hour

app = FastAPI(title="aesthetics roast")
state: dict = {}
hits: dict[str, list[float]] = defaultdict(list)  # ponytail: in-memory, per-process; redis if >1 worker


@app.on_event("startup")
def load():
    state["index"] = Index.load(DATA / "index.npz")
    graph = json.loads((DATA / "graph.json").read_text())
    state["graph"] = graph
    state["nodes"] = {n["slug"]: n for n in graph["nodes"]}
    state["ratings"] = {n["slug"]: n["mainstream"] for n in graph["nodes"] if n.get("mainstream") is not None}
    state.setdefault("encoder", Encoder(masked=state["index"].masked_faces))


def client_ip(request: Request) -> str:
    """Behind nginx (which appends the real client to X-Forwarded-For) trust the LAST hop it added;
    from anywhere else ignore the header, since a client can forge it to dodge the rate limit."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if request.client.host in ("127.0.0.1", "::1") or request.client.host.startswith("172."):  # local nginx via docker bridge
        return forwarded.split(",")[-1].strip() or request.client.host
    return request.client.host


def check_rate(ip: str):
    now = time.time()
    hits[ip] = [t for t in hits[ip] if now - t < RATE_WINDOW]
    if len(hits[ip]) >= RATE_LIMIT:
        raise HTTPException(429, f"limit is {RATE_LIMIT} analyses per hour")
    hits[ip].append(now)


@app.post("/api/analyze")
async def analyze(request: Request, images: list[UploadFile] = File(...)):
    if not MIN_IMAGES <= len(images) <= MAX_IMAGES:
        raise HTTPException(400, f"upload {MIN_IMAGES}-{MAX_IMAGES} images")
    check_rate(client_ip(request))
    index, encoder, nodes = state["index"], state["encoder"], state["nodes"]
    results, vecs = [], []
    for up in images:
        data = await up.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(400, f"{up.filename} is over {MAX_BYTES // 1_000_000} MB")
        try:
            vec = encoder.encode(data)
        except Exception:
            raise HTTPException(400, f"{up.filename} is not a readable image")
        vecs.append(vec)
        results.append({"filename": up.filename, **index.match(vec)})
    overall = index.match(aggregate(vecs))
    aesthetics = cover(results, overall["matches"][0]["slug"])
    slugs = {m["slug"] for r in results + [overall] for m in r["matches"]}
    return {"images": results, "overall": overall, "aesthetics": aesthetics, "basic_score": basic_score(results, state["ratings"]),
            "names": {s: nodes[s]["name"] for s in slugs}}


@app.get("/api/graph")
def graph():
    return state["graph"]


if WEB.exists():
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        return FileResponse(WEB / "index.html")
