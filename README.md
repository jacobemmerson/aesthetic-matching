# What's your aesthetic?

Upload up to ten photos and get placed on a map of 152 internet aesthetics, with a score from niche
to mainstream and a two-sentence verdict written by a local language model. Live at
[rate.jacobemmerson.com](http://rate.jacobemmerson.com).

## What differs from a plain embedding match

The baseline is nearest-centroid matching on raw SigLIP 2 image embeddings. On that baseline a
linear probe recovers a person's race from the embedding 60% of the time (chance is 14%), so
matches track who is in the photo rather than what they are wearing or where they are.

The served model changes three things:

1. Faces are blanked (YuNet detector) before encoding.
2. A LEACE projection removes the linear race and gender directions from the embedding.
3. A linear head over the 152 aesthetics, trained with group reweighting, replaces the centroid match.

| config (SigLIP 2) | race probe acc (chance .14) | gender probe acc (chance .50) | race TVD | gender TVD | top-1 | top-5 |
|---|---|---|---|---|---|---|
| centroid, no mitigation | 0.595 | 0.931 | 0.645 | 0.360 | 0.476 | 0.757 |
| head_rw + mask + LEACE (served) | 0.143 | 0.499 | 0.155 | 0.071 | 0.455 | 0.768 |

How these are measured (`pipeline/probe.py`, `pipeline/fairness.py`, `pipeline/evaluate.py`):

- Probe accuracy: cross-validated logistic regression predicting FairFace race or gender labels from
  the embeddings. The served config is at chance for both.
- TVD: total variation distance between each group's distribution of predicted aesthetics, measured
  on the half of the FairFace probe that LEACE was not fitted on. The shuffled-label noise floor is
  0.215 (race) and 0.084 (gender), so the served config is within noise.
- Top-1 / top-5: leave-one-out accuracy on the reference images. Top-5 is unchanged; top-1 drops
  2 points.

Every config tried is in `data/fairness_report_siglip.md` (SigLIP 2) and `data/fairness_report.md`
(the earlier CLIP backbone).

## How it works

**Reference data** (`pipeline/`, run once, in this order)

1. `scrape_wiki` pulls every aesthetic page into `data/wiki.json`.
2. `filter_nodes` applies `pipeline/exclude.txt` and keeps the top 152 by category in `data/nodes.json`.
3. `fetch_images` collects about 80 reference images per aesthetic through serper.dev, pooling four
   query phrasings (`outfit`, `room`, `aesthetic`, `style`). Resumable; `--slugs` refetches.
4. `popularity` records a search-demand signal; `data/mainstream.json` holds the hand-judged
   mainstream rating that becomes the score.
5. `faces` downloads the YuNet face detector (ONNX, gitignored).
6. `probe`, `debias`, `fairness`, `evaluate` produce the bias and accuracy numbers above.
7. `build_index` embeds the references, prunes near-duplicates and bare portraits, fits the
   spherical UMAP layout, and writes `data/index.npz` and `data/graph.json`.

**Serving** (`server/`, FastAPI). SigLIP 2 (`ViT-B-16-SigLIP2`, `webli`, via open_clip). The index
records its backbone, so the server loads the matching one.

- Each photo gets a softmax over the 152 aesthetics. Its labels are the top match plus any runner-up
  with at least a third of the top probability.
- The overall distribution is the mean over photos. The verdict lists up to five labels by mass.
- The score is the probability-weighted mainstream rating, rescaled to 0-100. Lower is more niche.
- The statement comes from Ollama (`llama3.1:8b` by default). Ten static lines cover Ollama being down.
- Rate limit: 5 analyses per IP per hour (`RATE_LIMIT`). `X-Forwarded-For` is trusted only from the
  local proxy, so clients cannot spoof it.

**Frontend** (`web/`, React + Vite + sigma.js). The layout is a unit sphere rotated in
`web/src/lib/sphere.js` and projected into sigma's 2D space each frame. Hover follows edges two hops
out, click pins the paths, drag rotates. Press `d` or add `?dev` for per-photo distributions.

## Run locally

```
uv sync
uv run python -m pipeline.faces          # once: fetches the face detector into data/
uv run uvicorn server.app:app --reload   # :8000, serves web/dist when it exists
cd web && npm ci && npm run dev          # :5173, proxies /api to :8000
```

Tests: `uv run pytest` and `cd web && npm test && npx oxlint src`. Screenshots at two widths:
`cd web && npm run shots` (Playwright, writes `web/scripts/shots/`).

| env var | default | used by |
|---|---|---|
| `DATA_DIR` | `./data` | server, face model path |
| `RATE_LIMIT` | `5` per IP per hour, `0` disables | server |
| `OLLAMA_URL` | `http://localhost:11434` | statement |
| `OLLAMA_MODEL` | `llama3.1:8b` | statement |
| `CLIP_MODEL`, `CLIP_PRETRAINED` | `ViT-B-16-SigLIP2`, `webli` | `build_index` only (names predate the SigLIP switch) |
| `SERPER_API_KEY` | from `.env` | `fetch_images`, `popularity` |

Rebuild the served index after changing references:

```
uv run python -m pipeline.build_index --limit 5 --mask-faces --debias leace --debias-tag siglip --head reweighted   # smoke
uv run python -m pipeline.build_index --mask-faces --debias leace --debias-tag siglip --head reweighted
```

## Deploy

`docker compose up -d --build` builds the frontend and API into one image, mounts `data/` read-only
plus the Hugging Face cache, and binds 127.0.0.1:8000 and the tailnet address. Put nginx or a
Cloudflare Tunnel in front with `client_max_body_size 60m` and a 120 s read timeout. Ollama runs on
the host with `OLLAMA_HOST=0.0.0.0` so the container can reach it.

The server loads three files: `data/index.npz`, `data/graph.json`, and the gitignored face detector
ONNX. Everything else in `data/` is pipeline input or a report.

## Known issues

- Some macOS Safari installs drop every WebGL context. The map shows a notice and suggests another
  browser; Safari's Develop > Feature Flags > "GPU Process: WebGL" is the user-side workaround.
- 32 aesthetics (scene through yuppie, alphabetically) still use single-phrasing references.
  Refetch with `fetch_images --slugs ... --phrasings`, then rebuild.
- The frontend ships one 550 KB JavaScript chunk (framer-motion plus sigma).
- Near-duplicate nodes such as Goth and Gothic are not merged.
