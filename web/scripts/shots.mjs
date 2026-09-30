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
  async analyzing() { const p = await page(1280); await p.route('**/api/analyze', (r) => setTimeout(() => r.fulfill({ status: 200, contentType: 'application/json', body: analyze }), 8000)); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click(); await p.waitForTimeout(800); await shoot(p, 'analyzing-1280'); await p.context().close() },
  async error429() { const p = await page(1280); await p.route('**/api/analyze', (r) => r.fulfill({ status: 429, contentType: 'application/json', body: JSON.stringify({ detail: 'limit is 5 analyses per hour' }) })); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click(); await p.waitForTimeout(800); await shoot(p, 'error-429'); await p.context().close() },
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
  async reveal() {
    const p = await page(1280); await uploadAll(p); await p.getByRole('button', { name: 'Find my aesthetic' }).click()
    await p.waitForSelector('.graph canvas'); await p.waitForTimeout(1200); await shoot(p, 'reveal-mid')
    await p.waitForTimeout(5000); await shoot(p, 'reveal-done')
    const r = await page(1280, { reducedMotion: 'reduce' }); await uploadAll(r); await r.getByRole('button', { name: 'Find my aesthetic' }).click(); await r.waitForSelector('.graph canvas'); await r.waitForTimeout(800); await shoot(r, 'reveal-reduced')
    const one = await page(1280); await uploadAll(one, 1); await one.getByRole('button', { name: 'Find my aesthetic' }).click(); await one.waitForSelector('.graph canvas'); await one.waitForTimeout(4000); await shoot(one, 'result-one-photo')
    await p.context().close(); await r.context().close(); await one.context().close()
  },
}
for (const [name, fn] of Object.entries(shots)) if (!scenarios.length || scenarios.includes(name)) await fn()
await browser.close()
vite?.kill()
