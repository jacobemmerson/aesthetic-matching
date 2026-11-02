# What's your aesthetic?

Upload up to ten photos and get placed on a map of 152 internet aesthetics, with a score from niche
to mainstream and a two-sentence verdict written by a local vision-language model that sees the
photos with faces blanked. Live at
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
   spherical UMAP layout, relaxes it so clusters spread out (`relax_layout` re-applies that to an
   existing build), and writes `data/index.npz` and `data/graph.json`.
8. `export_onnx` writes the image tower to `data/encoder.onnx` (gitignored) so the server embeds
   photos with onnxruntime; torch and open_clip are a build-time dependency group, not in the image.

**Serving** (`server/`, FastAPI). SigLIP 2 (`ViT-B-16-SigLIP2`, `webli`), exported from open_clip to
ONNX and run with onnxruntime. The index records its backbone, so the server refuses a mismatched
encoder. `/api/analyze` streams one line per photo as it is embedded, then the verdict, then the
statement.

- Each photo gets a softmax over the 152 aesthetics. Its labels are the top match plus any runner-up
  with at least a third of the top probability.
- The overall distribution is the mean over photos. The verdict lists up to five labels by mass.
- The score is the probability-weighted mainstream rating, rescaled to 0-100. Lower is more niche.
- The statement comes from Qwen3-VL 4B behind `llama-server` (`deploy/llama-server.service`), which
  sees the photos face-blanked and downscaled to 336 px and is asked to roast the taste, not the
  person. Ten static lines cover the model being down.
- Rate limit: 5 analyses per IP per hour (`RATE_LIMIT`). `X-Forwarded-For` is trusted only from the
  local proxy, so clients cannot spoof it.

**Frontend** (`web/`, React + Vite + sigma.js). The layout is a unit sphere rotated in
`web/src/lib/sphere.js` and projected into sigma's 2D space each frame with perspective. Hover follows
edges two hops out and lights the names near the cursor, click pins the paths, drag rotates. The look
follows iOS: system font, light and dark from the OS, an accent tinted from the user's photos
(`web/src/lib/tint.js`), and one sheet (`web/src/Sheet.jsx`) that holds upload, analysis, the verdict
and the aesthetic cards: a column on desktop, a bottom sheet with detents on phones. Press `d` or add
`?dev` for per-photo distributions.

## Run locally

```
uv sync                                  # dev + pipeline groups; the Docker image installs only the runtime deps
uv run python -m pipeline.faces          # once: fetches the face detector into data/
uv run python -m pipeline.export_onnx    # once per backbone: writes data/encoder.onnx + encoder.json
uv run hf download Qwen/Qwen3-VL-4B-Instruct-GGUF Qwen3VL-4B-Instruct-Q4_K_M.gguf mmproj-Qwen3VL-4B-Instruct-F16.gguf --local-dir ~/.cache/llama.cpp   # the verdict model, once
llama-server -m ~/.cache/llama.cpp/Qwen3VL-4B-Instruct-Q4_K_M.gguf --mmproj ~/.cache/llama.cpp/mmproj-Qwen3VL-4B-Instruct-F16.gguf --port 8081 -np 1 -fa on -ngl 22   # or install deploy/llama-server.service
uv run uvicorn server.app:app --reload   # :8000, serves web/dist when it exists
cd web && npm ci && npm run dev          # :5173, proxies /api to :8000
```

Tests: `uv run pytest` and `cd web && npm test && npx oxlint src`. Screenshots at two widths:
`cd web && npm run shots` (Playwright, writes `web/scripts/shots/`).

| env var | default | used by |
|---|---|---|
| `DATA_DIR` | `./data` | server, face model path |
| `RATE_LIMIT` | `5` per IP per hour, `0` disables | server |
| `LLM_URL` | `http://localhost:8081` | statement: a llama-server with a vision model (`deploy/llama-server.service`) |
| `CLIP_MODEL`, `CLIP_PRETRAINED` | `ViT-B-16-SigLIP2`, `webli` | `build_index` and `export_onnx` (names predate the SigLIP switch) |
| `SERPER_API_KEY` | from `.env` | `fetch_images`, `popularity` |

Rebuild the served index after changing references:

```
uv run python -m pipeline.build_index --limit 5 --mask-faces --debias leace --debias-tag siglip --head reweighted   # smoke
uv run python -m pipeline.build_index --mask-faces --debias leace --debias-tag siglip --head reweighted
```

## Deploy

`docker compose up -d --build` builds the frontend and API into one image, mounts `data/` read-only,
and binds 127.0.0.1:8000 and the tailnet address. Put nginx or a Cloudflare Tunnel in front with
`client_max_body_size 60m` and a 120 s read timeout. `llama-server` runs on the host
(`deploy/llama-server.service`, bound to 0.0.0.0) so the container can reach it; if it is down the
statement falls back to a fixed line per score band.

The server loads `data/index.npz`, `data/graph.json`, `data/nodes.json` (infobox fields for the
cards), `data/encoder.json`, and the gitignored `encoder.onnx` and face detector ONNX. Everything else
in `data/` is pipeline input or a report.

## Known issues

- Some macOS Safari installs drop every WebGL context. The map shows a notice and suggests another
  browser; Safari's Develop > Feature Flags > "GPU Process: WebGL" is the user-side workaround.
- 32 aesthetics (scene through yuppie, alphabetically) still use single-phrasing references.
  Refetch with `fetch_images --slugs ... --phrasings`, then rebuild.
- The frontend ships one 550 KB JavaScript chunk (framer-motion plus sigma).
- Near-duplicate nodes such as Goth and Gothic are not merged.
