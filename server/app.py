import asyncio
import io
import json
import os
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from server.match import Encoder, Index, basic_score, mixture, verdict
from server.roast import statement, warm

DATA = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
WEB = Path(__file__).resolve().parent.parent / "web" / "dist"
MIN_IMAGES, MAX_IMAGES, MAX_BYTES = 1, 10, 5_000_000
RATE_LIMIT, RATE_WINDOW = int(os.environ.get("RATE_LIMIT", 5)), 3600  # analyses per IP per hour; 0 disables

app = FastAPI(title="aesthetics roast")
app.add_middleware(GZipMiddleware, minimum_size=1000)
NODE_FIELDS = ("slug", "name", "x", "y", "z", "description", "other_names", "key_values", "key_motifs", "key_colours", "decade_of_origin", "wiki_url")  # what the map and the card read
INFOBOX_FIELDS = ("key_motifs", "key_colours", "decade_of_origin")  # kept in nodes.json by the scrape but not carried into graph.json
state: dict = {}
hits: dict[str, list[float]] = defaultdict(list)  # ponytail: in-memory, per-process; redis if >1 worker


@app.on_event("startup")
def load():
    state["index"] = Index.load(DATA / "index.npz")
    graph = json.loads((DATA / "graph.json").read_text())
    extra = json.loads((DATA / "nodes.json").read_text()) if (DATA / "nodes.json").exists() else []
    state["graph"] = slim_graph(join_infobox(graph, extra))
    state["nodes"] = {n["slug"]: n for n in graph["nodes"]}
    state["ratings"] = {n["slug"]: n["mainstream"] for n in graph["nodes"] if n.get("mainstream") is not None}
    state.setdefault("encoder", Encoder(masked=state["index"].masked_faces, backbone=state["index"].backbone, path=DATA / "encoder.onnx"))


def join_infobox(graph: dict, nodes: list[dict]) -> dict:
    """Adds the infobox fields from nodes.json onto the graph's nodes by slug, so the card can show them without a rebuild."""
    by_slug = {n["slug"]: n for n in nodes}
    for n in graph["nodes"]:
        n.update({k: by_slug.get(n["slug"], {}).get(k) for k in INFOBOX_FIELDS})
    return graph


def slim_graph(graph: dict) -> dict:
    return {"nodes": [{k: n.get(k) for k in NODE_FIELDS} for n in graph["nodes"]],
            "edges": [{"source": e["source"], "target": e["target"]} for e in graph["edges"]]}


def client_ip(request: Request) -> str:
    """Behind nginx (which appends the real client to X-Forwarded-For) trust the LAST hop it added;
    from anywhere else ignore the header, since a client can forge it to dodge the rate limit."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if request.client.host in ("127.0.0.1", "::1") or request.client.host.startswith("172."):  # local nginx via docker bridge
        return forwarded.split(",")[-1].strip() or request.client.host
    return request.client.host


def check_rate(ip: str):
    if not RATE_LIMIT:
        return
    now = time.time()
    hits[ip] = [t for t in hits[ip] if now - t < RATE_WINDOW]
    if len(hits[ip]) >= RATE_LIMIT:
        raise HTTPException(429, f"limit is {RATE_LIMIT} analyses per hour")
    hits[ip].append(now)


@app.post("/api/analyze")
async def analyze(request: Request, images: list[UploadFile] = File(...)):
    """Streams newline-delimited JSON: one `photo` line per image as it is embedded, then `verdict`, then `statement`
    (the slow one, from the language model). Validation that can fail with a 4xx happens before the first byte."""
    if not MIN_IMAGES <= len(images) <= MAX_IMAGES:
        raise HTTPException(400, f"upload {MIN_IMAGES}-{MAX_IMAGES} images")
    check_rate(client_ip(request))
    uploads = []
    for up in images:
        data = await up.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(400, f"{up.filename} is over {MAX_BYTES // 1_000_000} MB")
        try:
            Image.open(io.BytesIO(data)).verify()
        except Exception:
            raise HTTPException(400, f"{up.filename} is not a readable image")
        uploads.append((up.filename, data))
    index, encoder, nodes = state["index"], state["encoder"], state["nodes"]

    async def lines():
        previews = [await asyncio.to_thread(encoder.preview, data) for _, data in uploads]  # face-masked, small: what the verdict model gets
        warming = asyncio.create_task(asyncio.to_thread(warm, previews))  # the verdict model encodes the photos while we match them
        results = []
        for k, (filename, data) in enumerate(uploads):
            try:
                vec = await asyncio.to_thread(encoder.encode, data)  # off the event loop: the model takes a few hundred ms
            except Exception:
                yield json.dumps({"kind": "error", "detail": f"{filename} could not be processed"}) + "\n"
                return
            r = {"filename": filename, **index.match(vec)}
            results.append(r)
            names = {m["slug"]: nodes[m["slug"]]["name"] for m in r["matches"]}
            yield json.dumps({"kind": "photo", "index": k, "name": names[r["matches"][0]["slug"]], "names": names, **r}) + "\n"
        mix = mixture(results)
        overall = {"matches": mix, **index.place([m["slug"] for m in mix[:3]])}  # the You dot sits by the mixture's top label
        aesthetics = verdict(results)
        score = basic_score(results, state["ratings"])
        slugs = {m["slug"] for r in results + [overall] for m in r["matches"]}
        yield json.dumps({"kind": "verdict", "overall": overall, "aesthetics": aesthetics, "basic_score": score,
                          "names": {s: nodes[s]["name"] for s in slugs}}) + "\n"
        await warming
        text = await asyncio.to_thread(statement, score, [nodes[a["slug"]]["name"] for a in aesthetics], previews)
        yield json.dumps({"kind": "statement", "statement": text}) + "\n"

    # identity encoding keeps GZipMiddleware from buffering the stream; X-Accel-Buffering does the same for nginx
    return StreamingResponse(lines(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "Content-Encoding": "identity", "X-Accel-Buffering": "no"})


@app.get("/api/graph")
def graph():
    return state["graph"]


if WEB.exists():
    app.mount("/assets", StaticFiles(directory=WEB / "assets"), name="assets")

    @app.get("/favicon.svg")
    def favicon():
        return FileResponse(WEB / "favicon.svg")

    @app.get("/{path:path}")
    def spa(path: str):
        return FileResponse(WEB / "index.html")
