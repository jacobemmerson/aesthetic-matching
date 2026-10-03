# What's your aesthetic?

Drop up to ten photos and get placed on a globe of 152 internet aesthetics, with a score from
niche to basic and a two-sentence verdict from a local language model. Names and descriptions
come from the [Aesthetics Wiki](https://aesthetics.fandom.com) (CC BY-SA). Photos are never stored.

## How it works

**Reference data** (`pipeline/`, run once, in this order)

1. `scrape_wiki` pulls every aesthetic page into `data/wiki.json`.
2. `filter_nodes` applies `pipeline/exclude.txt` (music genres, subcultures, unusable pages) and
   picks the top 152 by category into `data/nodes.json`.
3. `fetch_images` collects about 80 reference images per aesthetic through serper.dev, pooling four
   query phrasings (`outfit`, `room`, `aesthetic`, `style`). Resumable; `--slugs` refetches.
4. `popularity` records a search-demand signal; `data/mainstream.json` holds the hand-judged
   mainstream rating per aesthetic that becomes the score.
5. `faces` downloads the YuNet face detector (ONNX, gitignored) used for masking and pruning.
6. `probe`, `debias`, `fairness`, `evaluate` measure race and gender leakage and matching accuracy;
   see `docs/superpowers/specs/2026-09-30-bias-mitigation-design.md`.
7. `build_index` embeds the references, prunes near-duplicates and bare portraits, fits the
   spherical UMAP layout, and writes `data/index.npz` plus `data/graph.json`.

**Served model.** SigLIP 2 (`ViT-B-16-SigLIP2`, `webli`, through open_clip) with faces blanked
before encoding, a LEACE projection that removes race and gender directions, and a reweighted linear
head over the 152 aesthetics. The index records its backbone, so the server loads the same one.

| config (SigLIP 2, pooled refs) | race TVD | gender TVD | race acc (chance .14) | gender acc (chance .5) | LOO top1 | LOO top5 |
|---|---|---|---|---|---|---|
| centroid, no mitigation | 0.645 | 0.360 | 0.595 | 0.931 | 0.476 | 0.757 |
| head_rw + mask + LEACE (served) | 0.155 | 0.071 | 0.143 | 0.499 | 0.455 | 0.768 |

Full table in `data/fairness_report_siglip.md`.

**Scoring** (`server/match.py`)

- Each photo gets a softmax over all aesthetics. Its labels are the top match plus any runner-up
  with at least a third of the top probability, so a photo can carry two aesthetics.
- The overall distribution is the mean of the photo distributions. The "You" dot sits by its top
  label, nudged slightly toward the next two.
- The verdict is the union of photo labels ordered by mass, capped at five.
- The score is the probability-weighted mainstream rating, rescaled to 0 to 100 over the catalog.
  Lower is more niche.
- The statement comes from Ollama (`llama3.1:8b` by default) with a persona that roasts basic
  taste and welcomes obscure taste. Ten static lines cover the model being down.

**Frontend** (`web/`, React + Vite + sigma.js). The layout is a unit sphere rotated in
`web/src/lib/sphere.js` and projected into sigma's 2D space each frame. Hover crawls two hops
along the edges, click pins the paths, drag rotates with momentum. Press `d` or add `?dev` for the
per-photo match distributions.

## Run locally

```
uv sync
uv run python -m pipeline.faces          # once: fetches the face detector into data/
uv run uvicorn server.app:app --reload   # :8000, serves web/dist when it exists
cd web && npm ci && npm run dev          # :5173, proxies /api to :8000
```

Tests: `uv run pytest` and `cd web && npm test && npx oxlint src`. Screenshots at two widths:
`cd web && npm run shots` (Playwright, writes `web/scripts/shots/`).

Environment variables:

| name | default | used by |
|---|---|---|
| `DATA_DIR` | `./data` | server, face model path |
| `RATE_LIMIT` | `5` analyses per IP per hour, `0` disables | server |
| `OLLAMA_URL` | `http://localhost:11434` | statement |
| `OLLAMA_MODEL` | `llama3.1:8b` | statement |
| `CLIP_MODEL`, `CLIP_PRETRAINED` | `ViT-B-16-SigLIP2`, `webli` | `build_index` only; the names predate the SigLIP switch |
| `SERPER_API_KEY` | from `.env` | `fetch_images`, `popularity` |

Rebuild the served index after changing references:

```
uv run python -m pipeline.build_index --limit 5 --mask-faces --debias leace --debias-tag siglip --head reweighted   # smoke
uv run python -m pipeline.build_index --mask-faces --debias leace --debias-tag siglip --head reweighted
```

## Deploy

`docker compose up -d --build` builds the frontend and the API into one image, mounts `data/`
read-only and the Hugging Face cache, and binds 127.0.0.1:8000 plus the tailnet address. Put
nginx or a Cloudflare Tunnel in front with `client_max_body_size 60m` and a 120 s read timeout.
Ollama runs on the host with `OLLAMA_HOST=0.0.0.0` so the container can reach it. The rate limiter
trusts the last `X-Forwarded-For` hop only from the local proxy.

## Data files

The server loads three files: `data/index.npz`, `data/graph.json`, and the gitignored face
detector ONNX. Everything else in `data/` is pipeline input or a report. `data/img` (about 600 MB)
and the `image_vecs*`, `index_*`, `probe*`, `debias_*` variants are gitignored experiment
artefacts; the `_crops`, `_smoke` and CLIP-era ones can be deleted.

## Known issues

- Some macOS Safari installs drop every WebGL context, including on sigma's own demo and
  get.webgl.org. The map shows a notice and suggests another browser. Safari's Develop >
  Feature Flags > "GPU Process: WebGL" is the user-side workaround.
- 32 aesthetics (scene through yuppie, alphabetically) still have the old single-phrasing
  references; refetch with `fetch_images --slugs ... --phrasings` when serper credits allow, then
  rebuild.
- The frontend ships one 550 KB JavaScript chunk (framer-motion plus sigma).
- Near-duplicate nodes such as Goth and Gothic are not merged.

## Ideas

Read EXIF (city, date, camera) for sharper roasts without logging GPS; HEIC uploads via
`pillow-heif`; abstain when no aesthetic clears a confidence floor; calibrate the softmax
temperature on a labelled set; regenerate the statement when both sentences share an opener.
