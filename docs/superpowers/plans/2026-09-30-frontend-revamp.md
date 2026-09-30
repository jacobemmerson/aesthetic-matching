# Frontend Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the React UI in `web/` with a dark editorial design, an animated upload flow, a choreographed reveal onto the aesthetics graph, live graph exploration, and a downloadable share card.

**Architecture:** `App.jsx` is a small phase machine (`upload` → `analyzing` → `result`) that owns the files and the API result. Presentational components (`Upload.jsx`, `Analyzing.jsx`, `Result.jsx`, `Graph.jsx`, `Drawer.jsx`) render each phase. All non-trivial logic lives in pure modules under `web/src/lib/` (file acceptance, search, reveal steps, share-card layout) so it is unit-testable without a browser; the graph itself is verified by Playwright screenshots against a mocked API.

**Tech Stack:** React 19, Vite, sigma v3 + graphology + @sigma/node-image (already installed), framer-motion (new), vitest (new dev), @playwright/test (new dev, chromium only).

**Spec:** `docs/superpowers/specs/2026-09-30-frontend-revamp-design.md`

## Global Constraints

- **Commits:** one per task (or per logical step), on the current branch, conventional format `<type>(<scope>): <subject>` (type = feat|fix|docs|style|refactor|test|chore|perf; subject ≤ 50 chars, imperative, no period; scope `web`). Every commit message must end with exactly these two trailer lines:
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01EZHZ7qqrCK1Lcki6Tzb3px`.
  Never rewrite history (no amend, rebase, reset, force). Never commit `web/scripts/shots/` or `node_modules`.
- Backend API is unchanged and not to be edited: `GET /api/graph`, `POST /api/analyze` (multipart field `images`), response shapes in Task 1's fixture.
- New runtime dependency allowed: `framer-motion` only. New dev dependencies allowed: `vitest`, `@playwright/test`. Nothing else.
- Color tokens verbatim from the spec: `--bg #0b0b0d`, `--surface #141418`, `--border #26262c`, `--text #f2efe9`, `--muted #8a8794`, `--accent #ff4d6d`, `--accent-soft rgba(255,77,109,.18)`.
- Fonts: Google Fonts `Fraunces` (display) and `Inter` (UI), loaded from `index.html`.
- Upload limits mirror the API: max 10 files, ≤ 5,000,000 bytes each, MIME starting with `image/`.
- Copy verbatim: headline "What's your aesthetic?", button "Find my aesthetic", analyzing copy "Reading N photos with CLIP…", result headline "You are A · B · C", share button "Download card", share filename `my-aesthetic.png`.
- Footer attribution must remain: "Aesthetic names and descriptions are from the Aesthetics Wiki (CC BY-SA). Matching uses CLIP image embeddings. Your photos are not stored." with the wiki link to https://aesthetics.fandom.com.
- Works at 1280 px and 390 px widths; drawer becomes a bottom sheet under 800 px.
- `prefers-reduced-motion: reduce` disables the reveal choreography and springs (final frame shown immediately).
- Screenshots go to `web/scripts/shots/` (git-ignored). All Playwright runs mock `/api/analyze` with `web/scripts/fixtures/analyze.json`; never hit the real analyze endpoint (rate limited, 5/hour).

## Review Focus

1. Dropping 12 files, a 9 MB JPEG, and a PDF together: the first 10 valid images are accepted, the rest produce one inline notice naming why. (Task 2 tests `acceptFiles`.)
2. The API answers 429 while analyzing: the message "limit is 5 analyses per hour" shows inline, the photos remain, the phase returns to `upload`. (Task 2 Playwright shot `error-429`.)
3. A single photo: the reveal runs with one step and the headline still reads three names. (Task 4 tests `buildRevealSteps` with n = 1 and Task 4 shot `result-one-photo`.)
4. Window narrower than 800 px with the drawer open: the drawer is a bottom sheet and does not cover the search box. (Task 3 shot `drawer-390`.)
5. `navigator.share` missing (desktop): "Download card" downloads `my-aesthetic.png`. (Task 5 tests `shareOrDownload` with a stubbed navigator.)

---

### Task 1: Foundation — dependencies, theme, phase machine, screenshot harness

**Files:**
- Modify: `web/package.json` (deps + scripts), `web/index.html`, `web/vite.config.js`
- Create: `web/src/index.css` (replace), `web/src/App.jsx` (replace), `web/src/Upload.jsx`, `web/src/Analyzing.jsx`, `web/src/Result.jsx` (placeholders that later tasks fill), `web/scripts/shots.mjs`, `web/vitest.config.js`
- Delete contents of: `web/src/Graph.jsx` is rewritten in Task 3; leave it untouched in this task.
- Fixtures already present: `web/scripts/fixtures/analyze.json`, `photo1.jpg`, `photo2.jpg`, `photo3.jpg`

**Interfaces:**
- Produces: `App.jsx` state `{ phase, files, result, error }` and handlers passed down as props:
  `Upload({ files, onAdd(fileList), onRemove(index), onAnalyze(), error })`,
  `Analyzing({ files })`, `Result({ files, result, onReset() })`.
- Produces: `npm run shots` (Playwright) and `npm test` (vitest) scripts.

- [ ] **Step 1: Install dependencies**

```bash
cd web && npm i framer-motion && npm i -D vitest @playwright/test && npx playwright install chromium
```

- [ ] **Step 2: Add scripts and vitest config**

In `web/package.json` `"scripts"` add:

```json
"test": "vitest run",
"shots": "node scripts/shots.mjs"
```

Create `web/vitest.config.js`:

```js
import { defineConfig } from 'vitest/config'
export default defineConfig({ test: { include: ['src/**/*.test.js'] } })
```

Append to the repo `.gitignore`: `web/scripts/shots/`

- [ ] **Step 3: Theme and fonts**

Replace `web/index.html` head with:

```html
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="color-scheme" content="dark" />
<title>What's your aesthetic?</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
```

Replace `web/src/index.css` with the token block and base styles:

```css
:root {
  --bg: #0b0b0d; --surface: #141418; --border: #26262c; --text: #f2efe9; --muted: #8a8794;
  --accent: #ff4d6d; --accent-soft: rgba(255,77,109,.18);
  --display: 'Fraunces', Georgia, serif; --ui: 'Inter', system-ui, sans-serif;
}
* { box-sizing: border-box; }
html, body, #root { margin: 0; min-height: 100%; background: var(--bg); color: var(--text); font-family: var(--ui); }
h1, h2, .display { font-family: var(--display); font-weight: 500; letter-spacing: -0.01em; }
a { color: var(--text); }
button { font: inherit; }
.btn { font-family: var(--ui); font-weight: 600; font-size: 1rem; padding: 12px 24px; border-radius: 999px; border: 1px solid var(--border); background: var(--text); color: var(--bg); cursor: pointer; }
.btn.ghost { background: transparent; color: var(--text); }
.btn:disabled { opacity: .5; cursor: default; }
main { max-width: 1200px; margin: 0 auto; padding: 24px 16px; }
footer { color: var(--muted); font-size: .8rem; line-height: 1.5; padding: 32px 16px; max-width: 1200px; margin: 0 auto; }
footer a { color: var(--muted); }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
```

- [ ] **Step 4: Phase machine**

Replace `web/src/App.jsx`:

```jsx
import { useState } from 'react'
import Upload from './Upload.jsx'
import Analyzing from './Analyzing.jsx'
import Result from './Result.jsx'
import { acceptFiles } from './lib/files.js'

export default function App() {
  const [phase, setPhase] = useState('upload')
  const [files, setFiles] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const onAdd = (list) => {
    const { accepted, notice } = acceptFiles(files, [...list])
    setFiles(accepted); setError(notice)
  }
  const onRemove = (i) => setFiles((f) => f.filter((_, k) => k !== i))

  const onAnalyze = async () => {
    setPhase('analyzing'); setError('')
    const body = new FormData()
    files.forEach((f) => body.append('images', f))
    try {
      const r = await fetch('/api/analyze', { method: 'POST', body })
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
      setResult(await r.json()); setPhase('result')
    } catch (e) { setError(e.message || 'Something went wrong'); setPhase('upload') }
  }
  const onReset = () => { setFiles([]); setResult(null); setError(''); setPhase('upload') }

  return (
    <>
      {phase === 'upload' && <Upload files={files} onAdd={onAdd} onRemove={onRemove} onAnalyze={onAnalyze} error={error} />}
      {phase === 'analyzing' && <Analyzing files={files} />}
      {phase === 'result' && <Result files={files} result={result} onReset={onReset} />}
      <footer>Aesthetic names and descriptions are from the <a href="https://aesthetics.fandom.com">Aesthetics Wiki</a> (CC BY-SA). Matching uses CLIP image embeddings. Your photos are not stored.</footer>
    </>
  )
}
```

Create `web/src/lib/files.js` with a stub (Task 2 implements it fully, its test lives there):

```js
export const MAX_FILES = 10
export const MAX_BYTES = 5_000_000
export function acceptFiles(existing, incoming) {
  return { accepted: [...existing, ...incoming].slice(0, MAX_FILES), notice: '' }
}
```

Create placeholder components so the app renders in every phase:

`web/src/Upload.jsx`:
```jsx
export default function Upload({ files, onAdd, onRemove, onAnalyze, error }) {
  return (
    <main>
      <h1>What's your aesthetic?</h1>
      <input type="file" accept="image/*" multiple onChange={(e) => onAdd(e.target.files)} />
      <ul>{files.map((f, i) => <li key={i}>{f.name} <button onClick={() => onRemove(i)}>remove</button></li>)}</ul>
      {error && <p role="alert">{error}</p>}
      {files.length > 0 && <button className="btn" onClick={onAnalyze}>Find my aesthetic</button>}
    </main>
  )
}
```

`web/src/Analyzing.jsx`:
```jsx
export default function Analyzing({ files }) {
  return <main><p>Reading {files.length} photos with CLIP…</p></main>
}
```

`web/src/Result.jsx`:
```jsx
export default function Result({ files, result, onReset }) {
  const names = result.overall.map((m) => result.names[m.slug]).join(' · ')
  return <main><h1>You are {names}</h1><button className="btn ghost" onClick={onReset}>Start over</button></main>
}
```

- [ ] **Step 5: Screenshot harness**

Create `web/scripts/shots.mjs`. It starts nothing itself; it expects a dev server on `http://localhost:5173` (run `npx vite --port 5173` in another shell, or the script starts one with `child_process.spawn` if the port is closed). It mocks `/api/analyze` with the fixture and proxies `/api/graph` to the real API at `http://127.0.0.1:8000` (read-only, unlimited).

```js
import { chromium } from '@playwright/test'
import { spawn } from 'node:child_process'
import { readFileSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const here = path.dirname(fileURLToPath(import.meta.url))
const fixtures = path.join(here, 'fixtures')
const out = path.join(here, 'shots')
mkdirSync(out, { recursive: true })
const analyze = readFileSync(path.join(fixtures, 'analyze.json'), 'utf8')
const photos = [1, 2, 3].map((n) => path.join(fixtures, `photo${n}.jpg`))

async function portOpen(port) {
  try { await fetch(`http://localhost:${port}`); return true } catch { return false }
}

const externalServer = await portOpen(5173)
const vite = externalServer ? null : spawn('npx', ['vite', '--port', '5173'], { cwd: path.join(here, '..'), stdio: 'ignore' })
for (let i = 0; i < 40 && !(await portOpen(5173)); i++) await new Promise((r) => setTimeout(r, 500))

const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] })
const scenarios = process.argv.slice(2)  // optional filter, e.g. `node scripts/shots.mjs result`

export async function page(width, { reducedMotion = 'no-preference' } = {}) {
  const ctx = await browser.newContext({ viewport: { width, height: width < 800 ? 844 : 900 }, reducedMotion })
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.error('PAGE ERROR', e.message))
  await p.route('**/api/analyze', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: analyze }))
  await p.goto('http://localhost:5173')
  return p
}

export async function uploadAll(p, count = 3) {
  await p.setInputFiles('input[type=file]', photos.slice(0, count))
}

export async function shoot(p, name) {
  await p.screenshot({ path: path.join(out, `${name}.png`), fullPage: true })
  console.log('shot', name)
}

const shots = {
  async upload() { for (const w of [1280, 390]) { const p = await page(w); await shoot(p, `upload-empty-${w}`); await uploadAll(p); await p.waitForTimeout(900); await shoot(p, `upload-files-${w}`); await p.context().close() } },
  async result() { for (const w of [1280, 390]) { const p = await page(w); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click(); await p.waitForTimeout(6000); await shoot(p, `result-${w}`); await p.context().close() } },
}
for (const [name, fn] of Object.entries(shots)) if (!scenarios.length || scenarios.includes(name)) await fn()
await browser.close()
vite?.kill()
```

Later tasks append scenarios to the `shots` object (the file is shared; each task adds its own keys and never removes others).

- [ ] **Step 6: Verify**

```bash
cd web && npm test && npm run build && npm run shots
```
Expected: vitest reports "no test files found" is NOT acceptable — add `src/lib/files.test.js` with one trivial passing assertion (`expect(MAX_FILES).toBe(10)`) so the runner is proven. Build succeeds. `scripts/shots/upload-empty-1280.png`, `upload-files-1280.png`, `result-1280.png` and the 390 variants exist; open them with Read and confirm dark background, headline in serif, and "You are Shabby Chic · Deathrock · Vaporwave" in the result shot.

---

### Task 2: Upload and analyzing experience

**Files:**
- Modify: `web/src/lib/files.js`, `web/src/Upload.jsx`, `web/src/Analyzing.jsx`, `web/src/index.css` (append), `web/scripts/shots.mjs` (append scenario)
- Test: `web/src/lib/files.test.js`

**Interfaces:**
- Consumes: props from Task 1 (`files, onAdd, onRemove, onAnalyze, error`).
- Produces: `acceptFiles(existing: File[], incoming: File[]) -> { accepted: File[], notice: string }`.

- [ ] **Step 1: Write the failing tests**

`web/src/lib/files.test.js`:
```js
import { describe, expect, it } from 'vitest'
import { acceptFiles, MAX_BYTES, MAX_FILES } from './files.js'

const img = (name, size = 1000, type = 'image/jpeg') => ({ name, size, type })

describe('acceptFiles', () => {
  it('keeps valid images and appends to existing', () => {
    const { accepted, notice } = acceptFiles([img('a.jpg')], [img('b.png', 10, 'image/png')])
    expect(accepted.map((f) => f.name)).toEqual(['a.jpg', 'b.png'])
    expect(notice).toBe('')
  })
  it('drops non-images and oversized files with a notice naming why', () => {
    const { accepted, notice } = acceptFiles([], [img('doc.pdf', 10, 'application/pdf'), img('big.jpg', MAX_BYTES + 1), img('ok.jpg')])
    expect(accepted.map((f) => f.name)).toEqual(['ok.jpg'])
    expect(notice).toMatch(/doc\.pdf.*not an image/i)
    expect(notice).toMatch(/big\.jpg.*5 MB/i)
  })
  it('caps at MAX_FILES and says how many were left out', () => {
    const many = Array.from({ length: 12 }, (_, i) => img(`p${i}.jpg`))
    const { accepted, notice } = acceptFiles([], many)
    expect(accepted).toHaveLength(MAX_FILES)
    expect(notice).toMatch(/2 more/)
  })
  it('ignores exact duplicates (same name and size)', () => {
    const { accepted } = acceptFiles([img('a.jpg')], [img('a.jpg')])
    expect(accepted).toHaveLength(1)
  })
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd web && npx vitest run src/lib/files.test.js`
Expected: FAIL (notice is always '' and no size/type filtering).

- [ ] **Step 3: Implement**

`web/src/lib/files.js`:
```js
export const MAX_FILES = 10
export const MAX_BYTES = 5_000_000

export function acceptFiles(existing, incoming) {
  const reasons = []
  const accepted = [...existing]
  const seen = new Set(existing.map((f) => `${f.name}:${f.size}`))
  let overflow = 0
  for (const f of incoming) {
    if (!f.type.startsWith('image/')) { reasons.push(`${f.name} is not an image`); continue }
    if (f.size > MAX_BYTES) { reasons.push(`${f.name} is over 5 MB`); continue }
    const key = `${f.name}:${f.size}`
    if (seen.has(key)) continue
    if (accepted.length >= MAX_FILES) { overflow++; continue }
    seen.add(key); accepted.push(f)
  }
  if (overflow) reasons.push(`only ${MAX_FILES} photos allowed, ${overflow} more left out`)
  return { accepted, notice: reasons.join('. ') }
}
```

- [ ] **Step 4: Run tests**

Run: `cd web && npm test` — Expected: all pass.

- [ ] **Step 5: Upload component with framer-motion**

Replace `web/src/Upload.jsx`:
```jsx
import { useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { MAX_FILES } from './lib/files.js'

const fan = (i, n) => ({ rotate: (i - (n - 1) / 2) * 6, y: Math.abs(i - (n - 1) / 2) * 6 })

export default function Upload({ files, onAdd, onRemove, onAnalyze, error }) {
  const [over, setOver] = useState(false)
  const input = useRef(null)
  return (
    <main className="hero">
      <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .6 }}>What's your aesthetic?</motion.h1>
      <p className="sub">Drop a few photos from your life. We'll place them on the map of every internet aesthetic.</p>

      <div className={'drop' + (over ? ' over' : '')} role="button" tabIndex={0}
        onClick={() => input.current.click()} onKeyDown={(e) => e.key === 'Enter' && input.current.click()}
        onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); onAdd(e.dataTransfer.files) }}>
        <span>Drop up to {MAX_FILES} photos here, or click to choose</span>
        <small>JPEG or PNG, under 5 MB each. Nothing is stored.</small>
        <input ref={input} type="file" accept="image/*" multiple hidden onChange={(e) => { onAdd(e.target.files); e.target.value = '' }} />
      </div>

      {error && <p className="notice" role="alert">{error}</p>}

      <motion.ul className="stack" layout>
        <AnimatePresence>
          {files.map((f, i) => (
            <motion.li key={`${f.name}:${f.size}`} layout
              initial={{ opacity: 0, scale: .6, ...fan(i, files.length) }}
              animate={{ opacity: 1, scale: 1, rotate: 0, y: 0 }}
              exit={{ opacity: 0, scale: .6 }}
              transition={{ type: 'spring', stiffness: 260, damping: 22, delay: i * .05 }}>
              <img src={URL.createObjectURL(f)} alt="" />
              <button className="remove" aria-label={`remove ${f.name}`} onClick={() => onRemove(i)}>×</button>
            </motion.li>
          ))}
        </AnimatePresence>
      </motion.ul>

      <AnimatePresence>
        {files.length > 0 && (
          <motion.button className="btn" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} onClick={onAnalyze}>
            Find my aesthetic
          </motion.button>
        )}
      </AnimatePresence>
    </main>
  )
}
```

Replace `web/src/Analyzing.jsx`:
```jsx
import { motion } from 'framer-motion'

export default function Analyzing({ files }) {
  return (
    <main className="hero">
      <ul className="strip">
        {files.map((f, i) => (
          <motion.li key={`${f.name}:${f.size}`} layoutId={`${f.name}:${f.size}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * .04 }}>
            <img src={URL.createObjectURL(f)} alt="" /><span className="scan" />
          </motion.li>
        ))}
      </ul>
      <p className="display analyzing">Reading {files.length} photo{files.length === 1 ? '' : 's'} with CLIP…</p>
      <div className="bar" role="progressbar" aria-busy="true"><span /></div>
    </main>
  )
}
```

Append to `web/src/index.css`:
```css
.hero { min-height: calc(100vh - 120px); display: flex; flex-direction: column; justify-content: center; gap: 20px; }
.hero h1 { font-size: clamp(2.6rem, 7vw, 5.5rem); margin: 0; line-height: .95; }
.sub { color: var(--muted); font-size: 1.1rem; margin: 0; max-width: 40ch; }
.drop { border: 1px dashed var(--border); border-radius: 16px; padding: 44px 24px; text-align: center; cursor: pointer; background: var(--surface); display: flex; flex-direction: column; gap: 6px; transition: border-color .2s, background .2s; }
.drop.over, .drop:hover { border-color: var(--accent); background: #17151a; }
.drop small { color: var(--muted); }
.notice { color: var(--accent); margin: 0; }
.stack, .strip { list-style: none; display: flex; flex-wrap: wrap; gap: 12px; margin: 0; padding: 0; }
.stack li { position: relative; width: 132px; height: 132px; border-radius: 12px; overflow: hidden; background: var(--surface); box-shadow: 0 10px 30px rgba(0,0,0,.5); }
.stack img, .strip img { width: 100%; height: 100%; object-fit: cover; display: block; }
.remove { position: absolute; top: 6px; right: 6px; width: 26px; height: 26px; border-radius: 50%; border: 0; background: rgba(0,0,0,.6); color: #fff; cursor: pointer; }
.strip li { position: relative; width: 72px; height: 72px; border-radius: 8px; overflow: hidden; }
.scan { position: absolute; inset: 0; background: linear-gradient(120deg, transparent 30%, rgba(255,77,109,.35) 50%, transparent 70%); background-size: 200% 100%; animation: scan 1.2s linear infinite; }
@keyframes scan { from { background-position: 200% 0 } to { background-position: -200% 0 } }
.analyzing { font-size: 1.6rem; margin: 0; }
.bar { height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; max-width: 420px; }
.bar span { display: block; height: 100%; width: 40%; background: var(--accent); animation: slide 1.1s ease-in-out infinite; }
@keyframes slide { from { transform: translateX(-100%) } to { transform: translateX(250%) } }
```

- [ ] **Step 6: Screenshot scenarios**

Append to `shots` in `web/scripts/shots.mjs`:
```js
async analyzing() { const p = await page(1280); await p.route('**/api/analyze', (r) => setTimeout(() => r.fulfill({ status: 200, contentType: 'application/json', body: analyze }), 8000)); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click(); await p.waitForTimeout(800); await shoot(p, 'analyzing-1280'); await p.context().close() },
async error429() { const p = await page(1280); await p.route('**/api/analyze', (r) => r.fulfill({ status: 429, contentType: 'application/json', body: JSON.stringify({ detail: 'limit is 5 analyses per hour' }) })); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click(); await p.waitForTimeout(800); await shoot(p, 'error-429'); await p.context().close() },
```
Note: routes registered later win in Playwright, so the per-scenario `p.route` overrides the default from `page()`.

- [ ] **Step 7: Verify**

```bash
cd web && npm test && npm run build && npm run shots upload analyzing error429
```
Read the PNGs: fanned-then-settled thumbnails with remove buttons, the analyzing strip with shimmer and bar, and the 429 shot showing the notice with the three photos still present and the button visible.

---

### Task 3: Graph rewrite — dark theme, hover highlighting, tooltip, drawer, search

**Files:**
- Replace: `web/src/Graph.jsx`
- Create: `web/src/Drawer.jsx`, `web/src/lib/search.js`, `web/src/lib/search.test.js`
- Modify: `web/src/Result.jsx` (mount Graph in a placeholder layout; Task 4 finishes it), `web/src/index.css` (append), `web/scripts/shots.mjs` (append)

**Interfaces:**
- Consumes: `result` (fixture shape), `files`.
- Produces: `searchNodes(nodes, query, limit = 8) -> node[]`.
- Produces: `Graph({ graph, result, files, onReady(api) })` where `api = { flyTo(slug | 'photo-<i>'), select(slug) }` and `Graph` renders the sigma canvas, tooltip, search box and drawer itself. Task 4 uses `api.flyTo` for the reveal and photo buttons.

- [ ] **Step 1: Failing search test**

`web/src/lib/search.test.js`:
```js
import { expect, it } from 'vitest'
import { searchNodes } from './search.js'

const nodes = [{ slug: 'goth', name: 'Goth' }, { slug: 'pastel-goth', name: 'Pastel Goth' }, { slug: 'gothic', name: 'Gothic' }, { slug: 'cottagecore', name: 'Cottagecore' }]

it('prefix matches rank before substring matches, case-insensitive', () => {
  expect(searchNodes(nodes, 'got').map((n) => n.slug)).toEqual(['goth', 'gothic', 'pastel-goth'])
})
it('empty query returns nothing and limit caps results', () => {
  expect(searchNodes(nodes, '')).toEqual([])
  expect(searchNodes(nodes, 'o', 2)).toHaveLength(2)
})
```

- [ ] **Step 2: Run, expect failure** — `cd web && npx vitest run src/lib/search.test.js`

- [ ] **Step 3: Implement**

`web/src/lib/search.js`:
```js
export function searchNodes(nodes, query, limit = 8) {
  const q = query.trim().toLowerCase()
  if (!q) return []
  const rank = (n) => { const s = n.name.toLowerCase(); return s.startsWith(q) ? 0 : s.includes(q) ? 1 : -1 }
  return nodes.map((n) => [rank(n), n]).filter(([r]) => r >= 0)
    .sort((a, b) => a[0] - b[0] || a[1].name.localeCompare(b[1].name))
    .slice(0, limit).map(([, n]) => n)
}
```

- [ ] **Step 4: Run tests** — `npm test` passes.

- [ ] **Step 5: Graph component**

Replace `web/src/Graph.jsx`:
```jsx
import { useEffect, useRef, useState } from 'react'
import Graphology from 'graphology'
import Sigma from 'sigma'
import { NodeImageProgram } from '@sigma/node-image'
import Drawer from './Drawer.jsx'
import { searchNodes } from './lib/search.js'

const SCALE = 60
const COLORS = { node: '#4a4740', edge: '#1e1e23', hot: '#ff4d6d', label: '#f2efe9', dim: '#1c1c20' }

export default function Graph({ graph, result, files, onReady, photosVisible = true }) {
  const el = useRef(null)
  const sigmaRef = useRef(null)
  const [hover, setHover] = useState(null)      // { slug, x, y }
  const [selected, setSelected] = useState(null) // node object
  const [query, setQuery] = useState('')
  const nodes = Object.fromEntries(graph.nodes.map((n) => [n.slug, n]))
  const hot = new Set(result.images.map((i) => i.matches[0].slug))

  useEffect(() => {
    const g = new Graphology()
    graph.nodes.forEach((n) => g.addNode(n.slug, { x: n.x * SCALE, y: n.y * SCALE, label: n.name, size: hot.has(n.slug) ? 8 : 3, color: hot.has(n.slug) ? COLORS.hot : COLORS.node, zIndex: hot.has(n.slug) ? 2 : 0 }))
    graph.edges.forEach((e) => { if (g.hasNode(e.source) && g.hasNode(e.target) && !g.hasEdge(e.source, e.target)) g.addEdge(e.source, e.target, { color: COLORS.edge, size: .6 }) })
    result.images.forEach((img, k) => g.addNode(`photo-${k}`, { x: img.x * SCALE, y: img.y * SCALE, size: 20, type: 'image', image: URL.createObjectURL(files[k]), label: `your photo ${k + 1}`, color: COLORS.hot, zIndex: 3, hidden: !photosVisible }))

    const sigma = new Sigma(g, el.current, {
      nodeProgramClasses: { image: NodeImageProgram }, renderLabels: true, labelRenderedSizeThreshold: 7,
      labelColor: { color: COLORS.label }, labelFont: 'Inter', labelSize: 12, zIndex: true,
      nodeReducer: (node, data) => {
        const h = hoverRef.current
        if (!h) return data
        if (node === h || g.hasEdge(node, h) || g.hasEdge(h, node)) return { ...data, zIndex: 4, forceLabel: true }
        return { ...data, color: COLORS.dim, label: null, image: undefined, type: data.type === 'image' ? 'circle' : data.type }
      },
      edgeReducer: (edge, data) => {
        const h = hoverRef.current
        if (!h) return data
        return g.hasExtremity(edge, h) ? { ...data, color: COLORS.hot, size: 1.2, zIndex: 1 } : { ...data, hidden: true }
      },
    })
    sigmaRef.current = sigma
    sigma.on('enterNode', ({ node, event }) => { hoverRef.current = node; setHover({ slug: node, x: event.x, y: event.y }); sigma.refresh() })
    sigma.on('leaveNode', () => { hoverRef.current = null; setHover(null); sigma.refresh() })
    sigma.on('clickNode', ({ node }) => nodes[node] && setSelected(nodes[node]))
    sigma.on('clickStage', () => setSelected(null))
    const api = {
      flyTo: (id, ratio = .25, duration = 600) => sigma.getCamera().animate({ ...sigma.getNodeDisplayData(id), ratio }, { duration }),
      overview: (duration = 800) => sigma.getCamera().animate({ x: .5, y: .5, ratio: 1 }, { duration }),
      showPhoto: (k) => { g.setNodeAttribute(`photo-${k}`, 'hidden', false); sigma.refresh() },
      select: (slug) => setSelected(nodes[slug] || null),
    }
    onReady?.(api)
    return () => sigma.kill()
  }, [graph, result, files])

  const hoverRef = useRef(null)
  const hits = searchNodes(graph.nodes, query)
  const pick = (n) => { setQuery(''); sigmaRef.current && (sigmaRef.current.getCamera().animate({ ...sigmaRef.current.getNodeDisplayData(n.slug), ratio: .25 }, { duration: 600 }), setSelected(n)) }

  return (
    <div className="graph-shell">
      <div className="graph" ref={el} />
      <div className="search">
        <input placeholder="Find an aesthetic…" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Escape') setQuery(''); if (e.key === 'Enter' && hits[0]) pick(hits[0]) }} />
        {hits.length > 0 && <ul>{hits.map((n) => <li key={n.slug} onMouseDown={() => pick(n)}>{n.name}</li>)}</ul>}
      </div>
      {hover && nodes[hover.slug] && (
        <div className="tip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
          <strong>{nodes[hover.slug].name}</strong><span>{nodes[hover.slug].description.split(/(?<=\.)\s/)[0]}</span>
        </div>
      )}
      <Drawer node={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
```

Create `web/src/Drawer.jsx`:
```jsx
import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

export default function Drawer({ node, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <AnimatePresence>
      {node && (
        <motion.aside className="drawer" key={node.slug}
          initial={{ x: '100%', opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: '100%', opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}>
          <button className="close" aria-label="close" onClick={onClose}>×</button>
          <h2>{node.name}</h2>
          {node.other_names && <p className="aliases">{node.other_names}</p>}
          <p className="desc">{node.description}</p>
          {node.key_values && <p className="values"><span>Values</span> {node.key_values}</p>}
          <a href={node.wiki_url} target="_blank" rel="noreferrer">Read on the Aesthetics Wiki →</a>
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
```

Under 800 px the drawer's initial/exit use `y: '100%'` instead of `x`; implement by reading `window.matchMedia('(max-width: 799px)').matches` once per render into a `small` boolean and picking the axis.

Temporary `web/src/Result.jsx` for this task (Task 4 replaces it):
```jsx
import { useEffect, useState } from 'react'
import Graph from './Graph.jsx'

export default function Result({ files, result, onReset }) {
  const [graph, setGraph] = useState(null)
  useEffect(() => { fetch('/api/graph').then((r) => r.json()).then(setGraph) }, [])
  const names = result.overall.map((m) => result.names[m.slug]).join(' · ')
  return (
    <main className="result">
      <header className="result-head"><h1>You are {names}</h1><button className="btn ghost" onClick={onReset}>Start over</button></header>
      {graph && <Graph graph={graph} result={result} files={files} />}
    </main>
  )
}
```

Append to `web/src/index.css`:
```css
.result { padding-top: 16px; }
.result-head { display: flex; align-items: end; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.result-head h1 { font-size: clamp(1.8rem, 4vw, 3rem); margin: 0; }
.graph-shell { position: relative; height: calc(100vh - 220px); min-height: 480px; border: 1px solid var(--border); border-radius: 16px; overflow: hidden; background: #0e0e11; }
.graph { position: absolute; inset: 0; }
.search { position: absolute; top: 12px; left: 12px; width: min(280px, calc(100% - 24px)); z-index: 5; }
.search input { width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--border); background: rgba(20,20,24,.9); color: var(--text); font: inherit; }
.search ul { list-style: none; margin: 6px 0 0; padding: 4px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; }
.search li { padding: 8px 10px; border-radius: 6px; cursor: pointer; }
.search li:hover { background: var(--accent-soft); }
.tip { position: absolute; z-index: 6; pointer-events: none; max-width: 260px; background: rgba(20,20,24,.95); border: 1px solid var(--border); border-radius: 10px; padding: 8px 10px; font-size: .85rem; display: flex; flex-direction: column; gap: 2px; }
.tip span { color: var(--muted); }
.drawer { position: absolute; top: 0; right: 0; bottom: 0; width: min(380px, 100%); z-index: 7; background: rgba(20,20,24,.97); border-left: 1px solid var(--border); padding: 24px; overflow: auto; }
.drawer h2 { margin: 0 0 6px; font-size: 1.8rem; }
.aliases { color: var(--muted); font-style: italic; margin: 0 0 12px; }
.desc { line-height: 1.55; }
.values span { color: var(--muted); }
.close { position: absolute; top: 12px; right: 12px; width: 30px; height: 30px; border-radius: 50%; border: 1px solid var(--border); background: transparent; color: var(--text); cursor: pointer; }
@media (max-width: 799px) {
  .graph-shell { height: 70vh; }
  .drawer { top: auto; left: 0; right: 0; width: 100%; max-height: 55%; border-left: 0; border-top: 1px solid var(--border); border-radius: 16px 16px 0 0; }
}
```

- [ ] **Step 6: Screenshot scenarios**

Append to `shots`:
```js
async graph() {
  for (const w of [1280, 390]) {
    const p = await page(w); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click()
    await p.waitForSelector('.graph canvas'); await p.waitForTimeout(7000)
    await p.fill('.search input', 'goth'); await p.waitForTimeout(300); await shoot(p, `search-${w}`)
    await p.press('.search input', 'Enter'); await p.waitForTimeout(900); await shoot(p, `drawer-${w}`)
    if (w === 1280) { const c = await p.$('.graph canvas'); const b = await c.boundingBox(); await p.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await p.waitForTimeout(400); await shoot(p, 'hover-1280') }
    await p.context().close()
  }
},
```

- [ ] **Step 7: Verify**

`cd web && npm test && npm run build && npm run shots graph`. Read `search-1280.png` (dropdown with Goth first), `drawer-1280.png` (drawer open on Goth with description), `drawer-390.png` (bottom sheet, search box still visible above it), `hover-1280.png` (if the cursor landed on a node: neighbours lit, rest dimmed; if it landed on empty stage, note it in the report and move the cursor to the first hot node's screen position via `sigma` is not accessible from Playwright — instead use `p.mouse.move` over the label of a hot node found by `p.getByText('Deathrock')` if labels are DOM; they are canvas, so accept a stage hover if no node is under the cursor and say so).

---

### Task 4: Reveal sequence, photo jump buttons, reduced motion

**Files:**
- Create: `web/src/lib/reveal.js`, `web/src/lib/reveal.test.js`
- Replace: `web/src/Result.jsx`
- Modify: `web/src/Graph.jsx` (accept `photosVisible` already present; expose `api.showPhoto` already present), `web/src/index.css` (append), `web/scripts/shots.mjs` (append)

**Interfaces:**
- Consumes: `Graph` `onReady(api)` with `api.flyTo(id, ratio, duration)`, `api.overview(duration)`, `api.showPhoto(k)`.
- Produces: `buildRevealSteps(result, { reducedMotion }) -> Step[]` where `Step = { kind: 'overview' | 'photo' | 'frame' | 'headline', index?: number, delay: number }`, `runSteps(steps, handlers) -> () => void` (returns a cancel function).

- [ ] **Step 1: Failing tests**

`web/src/lib/reveal.test.js`:
```js
import { expect, it, vi } from 'vitest'
import { buildRevealSteps, runSteps } from './reveal.js'

const result = { images: [{}, {}, {}] }

it('builds overview, one photo step per image, a frame, then the headline', () => {
  const kinds = buildRevealSteps(result, {}).map((s) => s.kind)
  expect(kinds).toEqual(['overview', 'photo', 'photo', 'photo', 'frame', 'headline'])
  expect(buildRevealSteps(result, {}).filter((s) => s.kind === 'photo').map((s) => s.index)).toEqual([0, 1, 2])
})
it('single photo still yields a full sequence', () => {
  expect(buildRevealSteps({ images: [{}] }, {}).map((s) => s.kind)).toEqual(['overview', 'photo', 'frame', 'headline'])
})
it('reduced motion collapses to zero-delay steps in the same order', () => {
  const steps = buildRevealSteps(result, { reducedMotion: true })
  expect(steps.every((s) => s.delay === 0)).toBe(true)
  expect(steps.map((s) => s.kind)).toEqual(['overview', 'photo', 'photo', 'photo', 'frame', 'headline'])
})
it('runSteps calls handlers in order and can be cancelled', async () => {
  vi.useFakeTimers()
  const calls = []
  const cancel = runSteps([{ kind: 'overview', delay: 0 }, { kind: 'photo', index: 0, delay: 100 }, { kind: 'headline', delay: 100 }], { overview: () => calls.push('o'), photo: (i) => calls.push(`p${i}`), headline: () => calls.push('h') })
  await vi.advanceTimersByTimeAsync(150)
  expect(calls).toEqual(['o', 'p0'])
  cancel()
  await vi.advanceTimersByTimeAsync(500)
  expect(calls).toEqual(['o', 'p0'])
  vi.useRealTimers()
})
```

- [ ] **Step 2: Run, expect failure.**

- [ ] **Step 3: Implement**

`web/src/lib/reveal.js`:
```js
export const TIMING = { hold: 400, fly: 600, pop: 350, frame: 800 }

export function buildRevealSteps(result, { reducedMotion = false } = {}) {
  const d = (ms) => (reducedMotion ? 0 : ms)
  const steps = [{ kind: 'overview', delay: 0 }]
  result.images.forEach((_, index) => steps.push({ kind: 'photo', index, delay: d(index === 0 ? TIMING.hold : TIMING.fly + TIMING.pop) }))
  steps.push({ kind: 'frame', delay: d(TIMING.fly + TIMING.pop) })
  steps.push({ kind: 'headline', delay: d(TIMING.frame) })
  return steps
}

/** Fires handlers[step.kind](step.index) sequentially, each after its delay. Returns cancel(). */
export function runSteps(steps, handlers) {
  let cancelled = false
  let timer = null
  const go = (i) => {
    if (cancelled || i >= steps.length) return
    timer = setTimeout(() => { if (cancelled) return; handlers[steps[i].kind]?.(steps[i].index); go(i + 1) }, steps[i].delay)
  }
  go(0)
  return () => { cancelled = true; clearTimeout(timer) }
}
```

- [ ] **Step 4: Tests pass.**

- [ ] **Step 5: Result component with the reveal**

Replace `web/src/Result.jsx`:
```jsx
import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Graph from './Graph.jsx'
import { buildRevealSteps, runSteps, TIMING } from './lib/reveal.js'
import { shareOrDownload } from './lib/shareCard.js'

const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

export default function Result({ files, result, onReset }) {
  const [graph, setGraph] = useState(null)
  const [stage, setStage] = useState('reveal')   // 'reveal' | 'done'
  const [lit, setLit] = useState([])             // photo indexes shown so far
  const api = useRef(null)
  useEffect(() => { fetch('/api/graph').then((r) => r.json()).then(setGraph) }, [])

  const onReady = (a) => {
    api.current = a
    const cancel = runSteps(buildRevealSteps(result, { reducedMotion: reduced() }), {
      overview: () => a.overview(0),
      photo: (i) => { a.flyTo(`photo-${i}`, .3, reduced() ? 0 : TIMING.fly); setTimeout(() => { a.showPhoto(i); setLit((l) => [...l, i]) }, reduced() ? 0 : TIMING.fly) },
      frame: () => a.overview(reduced() ? 0 : TIMING.frame),
      headline: () => setStage('done'),
    })
    return cancel
  }

  const names = result.overall.map((m) => result.names[m.slug])
  return (
    <main className="result">
      <header className="result-head">
        <div>
          <AnimatePresence>{stage === 'done' && (
            <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5 }}>
              You are {names.map((n, i) => <span key={n}>{i > 0 && ' · '}<em>{n}</em></span>)}
            </motion.h1>
          )}</AnimatePresence>
          {stage === 'done' && (
            <motion.div className="chips" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .3 }}>
              {result.images.map((img, k) => (
                <button key={k} className="chip" onClick={() => api.current?.flyTo(`photo-${k}`, .3)}>
                  <img src={URL.createObjectURL(files[k])} alt="" /> {result.names[img.matches[0].slug]}
                </button>
              ))}
            </motion.div>
          )}
        </div>
        {stage === 'done' && (
          <motion.div className="actions" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .6 }}>
            <button className="btn" onClick={() => shareOrDownload(result, graph, files)}>Download card</button>
            <button className="btn ghost" onClick={onReset}>Start over</button>
          </motion.div>
        )}
      </header>
      {graph && <Graph graph={graph} result={result} files={files} onReady={onReady} photosVisible={false} />}
    </main>
  )
}
```

Until Task 5 exists, create `web/src/lib/shareCard.js` with a stub `export async function shareOrDownload() {}` so the import resolves (Task 5 replaces it).

Append to `web/src/index.css`:
```css
.result-head h1 em { font-style: normal; color: var(--accent); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.chip { display: inline-flex; align-items: center; gap: 8px; padding: 4px 12px 4px 4px; border-radius: 999px; border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; font-size: .9rem; }
.chip img { width: 28px; height: 28px; border-radius: 50%; object-fit: cover; }
.actions { display: flex; gap: 8px; }
```

- [ ] **Step 6: Screenshot scenarios**

Append to `shots`:
```js
async reveal() {
  const p = await page(1280); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click()
  await p.waitForSelector('.graph canvas'); await p.waitForTimeout(1200); await shoot(p, 'reveal-mid')
  await p.waitForTimeout(5000); await shoot(p, 'reveal-done')
  const r = await page(1280, { reducedMotion: 'reduce' }); await uploadAll(r); await r.getByRole('button', { name: 'Find my aesthetic' }).click(); await r.waitForSelector('.graph canvas'); await r.waitForTimeout(800); await shoot(r, 'reveal-reduced')
  const one = await page(1280); await uploadAll(one, 1); await one.getByRole('button', { name: 'Find my aesthetic' }).click(); await one.waitForSelector('.graph canvas'); await one.waitForTimeout(4000); await shoot(one, 'result-one-photo')
  await p.context().close(); await r.context().close(); await one.context().close()
},
```
Note: the fixture has three photos; for `result-one-photo` the mock still returns three results, so the reveal must not crash when `files[k]` is undefined for k ≥ 1 — guard `files[k]` in Graph (skip photo nodes without a file) and in the chips.

- [ ] **Step 7: Verify**

`cd web && npm test && npm run build && npm run shots reveal`. Read `reveal-mid.png` (no headline yet, camera near a photo), `reveal-done.png` (headline with accent names, chips, buttons, all photos placed), `reveal-reduced.png` (final frame immediately), `result-one-photo.png` (no crash, one chip).

---

### Task 5: Share card

**Files:**
- Replace: `web/src/lib/shareCard.js`
- Create: `web/src/lib/shareCard.test.js`
- Modify: `web/scripts/shots.mjs` (append)

**Interfaces:**
- Consumes: `result`, `graph` (nodes with x,y), `files`.
- Produces: `layoutCard(result, graph, W = 1080, H = 1350) -> { title: {x,y,size}, names: [{text,x,y,size}], map: {x,y,w,h}, dots: [{x,y,hot}], photos: [{index,x,y,r}], footer: {x,y,size} }` (pure), `drawCard(ctx, layout, images: HTMLImageElement[], hostname)`, `shareOrDownload(result, graph, files)`.

- [ ] **Step 1: Failing tests**

`web/src/lib/shareCard.test.js`:
```js
import { expect, it, vi } from 'vitest'
import { layoutCard, shareOrDownload } from './shareCard.js'

const graph = { nodes: [{ slug: 'a', x: -1, y: -1 }, { slug: 'b', x: 1, y: 1 }, { slug: 'c', x: 0, y: 0 }] }
const result = { overall: [{ slug: 'a' }, { slug: 'b' }, { slug: 'c' }], names: { a: 'Alpha', b: 'Beta', c: 'Gamma' }, images: [{ x: 0, y: 0, matches: [{ slug: 'c' }] }] }

it('lays out three names and maps every node and photo inside the map box', () => {
  const L = layoutCard(result, graph)
  expect(L.names.map((n) => n.text)).toEqual(['Alpha', 'Beta', 'Gamma'])
  expect(L.dots).toHaveLength(3)
  for (const d of [...L.dots, ...L.photos]) {
    expect(d.x).toBeGreaterThanOrEqual(L.map.x); expect(d.x).toBeLessThanOrEqual(L.map.x + L.map.w)
    expect(d.y).toBeGreaterThanOrEqual(L.map.y); expect(d.y).toBeLessThanOrEqual(L.map.y + L.map.h)
  }
  expect(L.dots.filter((d) => d.hot).map((d) => d.slug)).toEqual(['c'])
})

it('falls back to a download when navigator.share is unavailable', async () => {
  const click = vi.fn()
  const a = { click, set href(v) { this._href = v }, set download(v) { this._dl = v } }
  const doc = { createElement: () => a }
  const canvas = { toBlob: (cb) => cb(new Blob(['x'], { type: 'image/png' })) }
  const nav = {}
  const url = { createObjectURL: () => 'blob:x', revokeObjectURL: vi.fn() }
  await shareOrDownload(result, graph, [], { render: async () => canvas, navigator: nav, document: doc, URL: url })
  expect(click).toHaveBeenCalled()
  expect(a._dl).toBe('my-aesthetic.png')
})
```

- [ ] **Step 2: Run, expect failure.**

- [ ] **Step 3: Implement**

`web/src/lib/shareCard.js`:
```js
const BG = '#0b0b0d', TEXT = '#f2efe9', MUTED = '#8a8794', ACCENT = '#ff4d6d', DOT = '#4a4740'

export function layoutCard(result, graph, W = 1080, H = 1350) {
  const pad = 72
  const names = result.overall.map((m, i) => ({ text: result.names[m.slug], x: pad, y: 250 + i * 118, size: 96 }))
  const map = { x: pad, y: 640, w: W - 2 * pad, h: 560 }
  const xs = graph.nodes.map((n) => n.x), ys = graph.nodes.map((n) => n.y)
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
  const px = (x) => map.x + ((x - x0) / (x1 - x0 || 1)) * map.w
  const py = (y) => map.y + ((y - y0) / (y1 - y0 || 1)) * map.h
  const hot = new Set(result.images.map((i) => i.matches[0].slug))
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
  return {
    title: { x: pad, y: 160, size: 30 },
    names,
    map,
    dots: graph.nodes.map((n) => ({ slug: n.slug, x: px(n.x), y: py(n.y), hot: hot.has(n.slug) })),
    photos: result.images.map((img, index) => ({ index, x: clamp(px(img.x), map.x + 40, map.x + map.w - 40), y: clamp(py(img.y), map.y + 40, map.y + map.h - 40), r: 40 })),
    footer: { x: pad, y: H - 72, size: 26 },
  }
}

export function drawCard(ctx, L, images, hostname, W = 1080, H = 1350) {
  ctx.fillStyle = BG; ctx.fillRect(0, 0, W, H)
  ctx.fillStyle = MUTED; ctx.font = `500 ${L.title.size}px Inter, system-ui, sans-serif`; ctx.fillText('my aesthetic is', L.title.x, L.title.y)
  for (const n of L.names) { ctx.fillStyle = TEXT; ctx.font = `700 ${n.size}px Fraunces, Georgia, serif`; ctx.fillText(n.text, n.x, n.y) }
  for (const d of L.dots) { ctx.fillStyle = d.hot ? ACCENT : DOT; ctx.beginPath(); ctx.arc(d.x, d.y, d.hot ? 7 : 3, 0, Math.PI * 2); ctx.fill() }
  for (const p of L.photos) {
    const img = images[p.index]; if (!img) continue
    ctx.save(); ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.closePath(); ctx.clip()
    const s = Math.max((2 * p.r) / img.width, (2 * p.r) / img.height)
    ctx.drawImage(img, p.x - (img.width * s) / 2, p.y - (img.height * s) / 2, img.width * s, img.height * s); ctx.restore()
    ctx.strokeStyle = ACCENT; ctx.lineWidth = 4; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.stroke()
  }
  ctx.fillStyle = MUTED; ctx.font = `500 ${L.footer.size}px Inter, system-ui, sans-serif`; ctx.fillText(hostname, L.footer.x, L.footer.y)
}

const loadImage = (file) => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = URL.createObjectURL(file) })

async function renderCanvas(result, graph, files) {
  await document.fonts?.load('700 96px Fraunces').catch(() => {})
  const canvas = document.createElement('canvas'); canvas.width = 1080; canvas.height = 1350
  drawCard(canvas.getContext('2d'), layoutCard(result, graph), await Promise.all(files.map(loadImage)), location.hostname)
  return canvas
}

/** Web Share with the PNG on phones; download elsewhere. `deps` exists for tests. */
export async function shareOrDownload(result, graph, files, deps = {}) {
  const { render = renderCanvas, navigator: nav = navigator, document: doc = document, URL: url = URL } = deps
  const canvas = await render(result, graph, files)
  const blob = await new Promise((r) => canvas.toBlob(r, 'image/png'))
  const file = new File([blob], 'my-aesthetic.png', { type: 'image/png' })
  if (nav.share && nav.canShare?.({ files: [file] })) { try { await nav.share({ files: [file], title: 'My aesthetic' }); return } catch { /* user cancelled: fall through to download */ } }
  const a = doc.createElement('a'); a.href = url.createObjectURL(blob); a.download = 'my-aesthetic.png'; a.click()
  setTimeout(() => url.revokeObjectURL(a.href), 1000)
}
```

- [ ] **Step 4: Tests pass** (`File` and `Blob` exist in Node 20+/22).

- [ ] **Step 5: Screenshot scenario**

Append to `shots`:
```js
async card() {
  const p = await page(1280); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click()
  await p.waitForSelector('.graph canvas'); await p.waitForTimeout(7000)
  const [dl] = await Promise.all([p.waitForEvent('download'), p.getByRole('button', { name: 'Download card' }).click()])
  await dl.saveAs(path.join(out, 'card.png')); console.log('shot card')
  await p.context().close()
},
```

- [ ] **Step 6: Verify**

`cd web && npm test && npm run build && npm run shots card`. Read `scripts/shots/card.png`: 1080×1350, dark, "my aesthetic is", three names in serif, mini map with accent dots and three circular photos, hostname footer.

---

### Task 6: Cleanup and full pass

**Files:**
- Modify: `web/src/index.css` (remove dead rules from the old design if any remain), `web/src/App.jsx` (no changes expected), `web/README.md` (replace Vite boilerplate with 10 lines: how to run dev, tests, shots, build)

- [ ] **Step 1:** Delete any leftover CSS classes not referenced by any JSX (`grep -o 'className="[^"]*"' src/*.jsx` vs selectors in `index.css`).
- [ ] **Step 2:** `web/README.md`:
```md
# web
- `npm run dev` — Vite on :5173, proxies /api to :8000 (start the API with `docker compose up -d` at repo root)
- `npm test` — vitest unit tests for `src/lib`
- `npm run shots [scenario…]` — Playwright screenshots into `scripts/shots/` with a mocked analyze response
- `npm run build` — production build into `dist/` (served by the API container)
```
- [ ] **Step 3:** Full verification: `cd web && npm test && npm run build && npm run shots` (all scenarios). Read every PNG once; list any visual defect in the report rather than fixing outside scope.
