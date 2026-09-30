# Frontend revamp: dark editorial, choreographed reveal

Approved in chat on 2026-09-30. Replaces the current `web/src` UI. The backend API is unchanged.

## Look

- Near-black shell, one warm-red accent, off-white serif display type, light sans for UI.
- Tokens (CSS custom properties on `:root`): `--bg #0b0b0d`, `--surface #141418`,
  `--border #26262c`, `--text #f2efe9`, `--muted #8a8794`, `--accent #ff4d6d`,
  `--accent-soft rgba(255,77,109,.18)`.
- Fonts via Google Fonts: `Fraunces` (display, weights 500/700, `opsz` axis on) and `Inter`
  (UI). Fallbacks: Georgia / system-ui.
- Graph: nodes are dim bone dots (`#4a4740`), edges `#1e1e23`; matched nodes and photo nodes
  use the accent; labels in `--text`.
- No gradients, no sound, no per-aesthetic color theming.

## States (one page, `App.jsx` holds `phase: 'upload' | 'analyzing' | 'result'`)

1. **Upload.** Full-viewport hero: headline "What's your aesthetic?", one-line sub, a large
   drop zone (also click-to-choose). Dropped photos spring into a loosely fanned stack that
   settles into a row; each thumbnail has a remove button. The "Find my aesthetic" button
   appears once ≥1 photo is present. Limits mirror the API: max 10 photos, ≤5 MB each,
   `image/*` only; rejected files produce a short inline notice, never a dialog.
2. **Analyzing.** The row shrinks into a strip; each thumbnail carries a scanning shimmer;
   an indeterminate bar with copy "Reading N photos with CLIP…". The API is one call, so no
   fake per-photo progress. On API error (400/429/5xx/network) show the message inline and
   return to the upload phase with photos intact.
3. **Result.** Graph fills the viewport height minus a compact header. Reveal sequence:
   camera at overview (0.4 s hold) → for each photo in order: camera glides to its (x,y)
   (600 ms), photo node pops in with a spring, its top-1 match label lights up → after the
   last, camera pulls back to frame all photos (800 ms) → headline types in:
   "You are Shabby Chic · Deathrock · Vaporwave" (top-3 names), per-photo chips below,
   then the action buttons fade in. `prefers-reduced-motion` skips the choreography and
   shows the final frame immediately.

## Live exploration (result phase)

- Hover a node: it and its neighbours (graph edges) stay lit, everything else dims to 25 %
  opacity; a floating tooltip shows the name and the first sentence of its description.
- Click a node: a right-side drawer (bottom sheet under 800 px) with name, aliases
  (`other_names`), full description, key values, and a "Read on the Aesthetics Wiki" link.
  Escape or clicking the stage closes it.
- Search box (top-left of the graph): filters aesthetic names as you type (prefix and
  substring, case-insensitive, max 8 results); choosing one flies the camera there and
  opens its drawer.
- "Your photos" buttons under the headline jump the camera to each photo node.

## Share card

- "Download card" button renders a 1080×1350 PNG (Pinterest 4:5) on an offscreen canvas:
  `--bg` background, small "my aesthetic is" label, the top-3 names in Fraunces stacked
  large, a mini map (all node dots, matched nodes in accent, user photos drawn as circular
  clipped images at their (x,y)), footer with the site hostname.
- Uses `navigator.share` with the file when available (phones), else triggers a download
  named `my-aesthetic.png`. No server round trip.

## Non-goals

Sound; adaptive color themes; server changes; storing photos; analytics.

## Verification

- Unit tests (vitest) for the pure modules: file acceptance, search, reveal step builder,
  share-card layout.
- Screenshots via Playwright (chromium, headless, swiftshader) with the API mocked from
  `web/scripts/fixtures/analyze.json` for each phase at 1280 px and 390 px widths, plus
  hover, drawer-open and search states. Reviewed by eye.
- `npm run build` succeeds; container rebuild is done by the controller, not tasks.
