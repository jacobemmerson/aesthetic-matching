import { expect, it, vi } from 'vitest'
import { fitFontSize, layoutCard, shareOrDownload } from './shareCard.js'

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

it('shrinks a font until the text fits, but not below the floor', () => {
  const measure = (t, size) => t.length * size
  expect(fitFontSize(measure, 'abcd', 96, 200)).toBe(50)
  expect(fitFontSize(measure, 'abcd', 96, 1)).toBe(40)
  expect(fitFontSize(measure, 'ab', 96, 1000)).toBe(96)
})

it('rejects when the canvas cannot produce a blob', async () => {
  const canvas = { toBlob: (cb) => cb(null) }
  await expect(shareOrDownload(result, graph, [], { render: async () => canvas, navigator: {}, document: {}, URL: {} })).rejects.toThrow('could not render card')
})

it('does not download when the user cancels the share sheet', async () => {
  const click = vi.fn()
  const canvas = { toBlob: (cb) => cb(new Blob(['x'], { type: 'image/png' })) }
  const nav = { canShare: () => true, share: () => Promise.reject(Object.assign(new Error('cancelled'), { name: 'AbortError' })) }
  await shareOrDownload(result, graph, [], { render: async () => canvas, navigator: nav, document: { createElement: () => ({ click }) }, URL: {} })
  expect(click).not.toHaveBeenCalled()
})
