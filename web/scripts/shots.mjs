import { chromium } from '@playwright/test'
import { spawn } from 'node:child_process'
import { readFileSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const here = path.dirname(fileURLToPath(import.meta.url))
const fixtures = path.join(here, 'fixtures')
const out = path.join(here, 'shots')
mkdirSync(out, { recursive: true })
const fixture = JSON.parse(readFileSync(path.join(fixtures, 'analyze.json'), 'utf8'))
// the endpoint streams NDJSON: photo lines, then the verdict, then the statement
const analyze = [...fixture.images.map((img, index) => ({ kind: 'photo', index, name: fixture.names[img.matches[0].slug], names: Object.fromEntries(img.matches.map((m) => [m.slug, fixture.names[m.slug] || m.slug])), ...img })),
  { kind: 'verdict', overall: fixture.overall, aesthetics: fixture.aesthetics, basic_score: fixture.basic_score, names: fixture.names },
  { kind: 'statement', statement: fixture.statement }].map((m) => JSON.stringify(m)).join('\n') + '\n'
const NDJSON = 'application/x-ndjson'
const photos = [1, 2, 3].map((n) => path.join(fixtures, `photo${n}.jpg`))

async function portOpen(port) {
  try { await fetch(`http://localhost:${port}`); return true } catch { return false }
}

const PORT = process.env.PORT || 5173  // with API_URL, points the shots at another backend without touching a running dev server
const externalServer = await portOpen(PORT)
const vite = externalServer ? null : spawn('npx', ['vite', '--port', PORT], { cwd: path.join(here, '..'), stdio: 'ignore' })
for (let i = 0; i < 40 && !(await portOpen(PORT)); i++) await new Promise((r) => setTimeout(r, 500))

const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] })
const SCHEMES = ['light', 'dark']
const toResult = async (p) => { await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click(); await p.waitForTimeout(11000) }
const scenarios = process.argv.slice(2)  // optional filter, e.g. `node scripts/shots.mjs result`

export async function page(width, { reducedMotion = 'no-preference', colorScheme = 'dark' } = {}) {
  const ctx = await browser.newContext({ viewport: { width, height: width < 800 ? 844 : 900 }, reducedMotion, colorScheme })
  const p = await ctx.newPage()
  p.on('pageerror', (e) => console.error('PAGE ERROR', e.message))
  await p.route('**/api/analyze', (route) => route.fulfill({ status: 200, contentType: NDJSON, body: analyze }))
  await p.goto(`http://localhost:${PORT}`)
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
  async upload() { for (const colorScheme of SCHEMES) for (const w of [1280, 390]) { const p = await page(w, { colorScheme }); await p.waitForSelector('.graph canvas'); await p.waitForTimeout(800); await shoot(p, `upload-empty-${w}-${colorScheme}`); await uploadAll(p); await p.waitForTimeout(900); await shoot(p, `upload-files-${w}-${colorScheme}`); await p.context().close() } },
  async result() { for (const colorScheme of SCHEMES) for (const w of [1280, 390]) { const p = await page(w, { colorScheme }); await toResult(p); await shoot(p, `result-${w}-${colorScheme}`); await p.context().close() } },
  async detail() {
    for (const w of [1280, 390]) { const p = await page(w); await toResult(p); await p.locator('.row').first().click(); await p.waitForTimeout(1200); await p.getByRole('button', { name: 'More' }).click(); await p.waitForTimeout(400); await shoot(p, `detail-${w}`); await p.context().close() }
    const p = await page(390); await toResult(p)
    const handle = await p.locator('.handle-area').boundingBox()
    await p.mouse.move(handle.x + handle.width / 2, handle.y + 5); await p.mouse.down(); await p.mouse.move(handle.x + handle.width / 2, 800, { steps: 10 }); await p.mouse.up()
    await p.waitForTimeout(800); await shoot(p, 'sheet-peek-390'); await p.context().close()
  },
  async hover() { const p = await page(1280); await toResult(p); await p.mouse.move(980, 300); await p.waitForTimeout(400); await shoot(p, 'hover-1280'); await p.context().close() },
  async why() { const p = await page(1280); await toResult(p); await p.locator('.why .row').first().click(); await p.waitForTimeout(1200); await shoot(p, 'why-1280'); await p.context().close() },
  async analyzing() { const p = await page(1280); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click(); await p.waitForTimeout(1100); await shoot(p, 'analyzing-1280'); await p.context().close() },
  async error429() { const p = await page(1280); await p.route('**/api/analyze', (r) => r.fulfill({ status: 429, contentType: 'application/json', body: JSON.stringify({ detail: 'limit is 5 analyses per hour' }) })); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click(); await p.waitForTimeout(800); await shoot(p, 'error-429'); await p.context().close() },
  async reveal() {
    const p = await page(1280); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click()
    await p.waitForTimeout(4000); await shoot(p, 'reveal-mid')
    await p.waitForTimeout(6000); await shoot(p, 'reveal-done')
    const r = await page(1280, { reducedMotion: 'reduce' }); await uploadAll(r); await r.getByRole('button', { name: 'Find my aesthetic' }).click(); await r.waitForTimeout(1200); await shoot(r, 'reveal-reduced')
    const one = await page(1280); await uploadAll(one, 1); await one.getByRole('button', { name: 'Find my aesthetic' }).click(); await one.waitForTimeout(9000); await shoot(one, 'result-one-photo')
    await p.context().close(); await r.context().close(); await one.context().close()
  },
}
for (const [name, fn] of Object.entries(shots)) if (!scenarios.length || scenarios.includes(name)) await fn()
await browser.close()
vite?.kill()
