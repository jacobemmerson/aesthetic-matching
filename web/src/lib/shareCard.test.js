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
