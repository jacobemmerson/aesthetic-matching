const BG = '#0b0b0d', TEXT = '#f2efe9', MUTED = '#8a8794', ACCENT = '#ff4d6d', DOT = '#4a4740'

export function layoutCard(result, graph, W = 1080, H = 1350) {
  const pad = 72
  const map = { x: pad, y: 640, w: W - 2 * pad, h: 560 }
  const size = result.aesthetics.length <= 3 ? 96 : 68  // five lines of 68 end at y=586, above the map
  const names = result.aesthetics.map((a, i) => ({ text: result.names[a.slug], x: pad, y: 250 + i * Math.round(size * 1.23), size }))
  const xs = graph.nodes.map((n) => n.x), ys = graph.nodes.map((n) => n.y)
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
  const px = (x) => map.x + ((x - x0) / (x1 - x0 || 1)) * map.w
  const py = (y) => map.y + ((y - y0) / (y1 - y0 || 1)) * map.h
  const hot = new Set(result.aesthetics.map((a) => a.slug))
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
  return {
    title: { x: pad, y: 160, size: 30 },
    names,
    map,
    dots: graph.nodes.map((n) => ({ slug: n.slug, x: px(n.x), y: py(n.y), hot: hot.has(n.slug) })),
    photos: result.images.map((img, index) => ({ index, x: clamp(px(img.x), map.x + 40, map.x + map.w - 40), y: clamp(py(img.y), map.y + 40, map.y + map.h - 40), r: 40 })),
    footer: { x: pad, y: H - 72, size: 26 },
    score: { x: W - pad, y: H - 72, size: 26, text: `basic score ${result.basic_score} / 100` },
  }
}

export function fitFontSize(measure, text, size, maxWidth, floor = 40) {
  while (size > floor && measure(text, size) > maxWidth) size -= 2
  return size
}

export function drawCard(ctx, L, images, hostname, W = 1080, H = 1350) {
  ctx.fillStyle = BG; ctx.fillRect(0, 0, W, H)
  ctx.fillStyle = MUTED; ctx.font = `500 ${L.title.size}px Inter, system-ui, sans-serif`; ctx.fillText('my aesthetic is', L.title.x, L.title.y)
  const fontFor = (size) => `700 ${size}px Fraunces, Georgia, serif`
  for (const n of L.names) {
    const size = fitFontSize((t, sz) => { ctx.font = fontFor(sz); return ctx.measureText(t).width }, n.text, n.size, W - 2 * n.x)
    ctx.fillStyle = TEXT; ctx.font = fontFor(size); ctx.fillText(n.text, n.x, n.y)
  }
  for (const d of L.dots) { ctx.fillStyle = d.hot ? ACCENT : DOT; ctx.beginPath(); ctx.arc(d.x, d.y, d.hot ? 7 : 3, 0, Math.PI * 2); ctx.fill() }
  for (const p of L.photos) {
    const img = images[p.index]; if (!img) continue
    ctx.save(); ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.closePath(); ctx.clip()
    const s = Math.max((2 * p.r) / img.width, (2 * p.r) / img.height)
    ctx.drawImage(img, p.x - (img.width * s) / 2, p.y - (img.height * s) / 2, img.width * s, img.height * s); ctx.restore()
    ctx.strokeStyle = ACCENT; ctx.lineWidth = 4; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.stroke()
  }
  ctx.fillStyle = MUTED; ctx.font = `500 ${L.footer.size}px Inter, system-ui, sans-serif`; ctx.fillText(hostname, L.footer.x, L.footer.y)
  ctx.fillStyle = TEXT; ctx.font = `600 ${L.score.size}px Inter, system-ui, sans-serif`; ctx.textAlign = 'right'; ctx.fillText(L.score.text, L.score.x, L.score.y); ctx.textAlign = 'left'
}

// Resolves null on failure so one bad photo doesn't abort the card.
const loadImage = (file) => new Promise((res) => {
  const i = new Image(), src = URL.createObjectURL(file)
  i.onload = () => { URL.revokeObjectURL(src); res(i) }
  i.onerror = () => { URL.revokeObjectURL(src); res(null) }
  i.src = src
})

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
  if (!blob) throw new Error('could not render card')
  const file = new File([blob], 'my-aesthetic.png', { type: 'image/png' })
  if (nav.share && nav.canShare?.({ files: [file] })) { try { await nav.share({ files: [file], title: 'My aesthetic' }); return } catch (e) { if (e?.name === 'AbortError') return } }
  const a = doc.createElement('a'); a.href = url.createObjectURL(blob); a.download = 'my-aesthetic.png'; a.click()
  setTimeout(() => url.revokeObjectURL(a.href), 1000)
}
