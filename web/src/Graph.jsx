import { useEffect, useRef, useState } from 'react'
import Graphology from 'graphology'
import Sigma from 'sigma'
import { NodeImageProgram } from '@sigma/node-image'
import { drawDiscNodeLabel } from 'sigma/rendering'
import { useObjectUrls } from './lib/objectUrls.js'
import Drawer from './Drawer.jsx'
import { searchNodes } from './lib/search.js'
import { mixHex, tween } from './lib/tween.js'

const SCALE = 60
const COLORS = { node: '#4a4740', edge: '#1e1e23', bg: '#0b0b0d', hot: '#ff4d6d', label: '#f2efe9', dim: '#1c1c20', you: '#f2efe9' }
const HOVER_MS = 180

export default function Graph({ graph, result, files, onReady, photosVisible = true }) {
  const el = useRef(null)
  const sigmaRef = useRef(null)
  const hoverRef = useRef(null)   // node under the cursor (kept while the dim fades back out)
  const dimRef = useRef(0)        // 0 = nothing dimmed, 1 = fully focused on hoverRef
  const fadeRef = useRef(() => {})
  const urls = useObjectUrls(files)
  const [hover, setHover] = useState(null)      // { slug, x, y }
  const [selected, setSelected] = useState(null) // node object
  const [query, setQuery] = useState('')
  const nodes = Object.fromEntries(graph.nodes.map((n) => [n.slug, n]))
  const hot = new Set(result.aesthetics.map((a) => a.slug))
  const litAtStart = photosVisible ? hot : new Set()  // reveal lights matches via api.light

  useEffect(() => {
    const g = new Graphology()
    graph.nodes.forEach((n) => g.addNode(n.slug, { x: n.x * SCALE, y: n.y * SCALE, label: n.name, size: litAtStart.has(n.slug) ? 8 : 3, color: litAtStart.has(n.slug) ? COLORS.hot : COLORS.node, zIndex: litAtStart.has(n.slug) ? 2 : 0 }))
    graph.edges.forEach((e) => { if (g.hasNode(e.source) && g.hasNode(e.target) && !g.hasEdge(e.source, e.target)) g.addEdge(e.source, e.target, { color: COLORS.edge, size: .6 }) })
    result.images.forEach((img, k) => {
      const image = urls.get(files[k])
      if (image) g.addNode(`photo-${k}`, { x: img.x * SCALE, y: img.y * SCALE, size: photosVisible ? 20 : 0, type: 'image', image, color: COLORS.hot, zIndex: 3 })
    })
    g.addNode('overall', { x: result.overall.x * SCALE, y: result.overall.y * SCALE, size: photosVisible ? 11 : 0, label: 'you', color: COLORS.you, zIndex: 3 })

    const sigma = new Sigma(g, el.current, {
      nodeProgramClasses: { image: NodeImageProgram }, renderLabels: true, labelRenderedSizeThreshold: 7,
      labelColor: { color: COLORS.label }, labelFont: 'Inter', labelSize: 12, zIndex: true, defaultDrawNodeHover: drawDiscNodeLabel,
      nodeReducer: (node, data) => {
        const h = hoverRef.current, t = dimRef.current
        if (!h || t === 0) return data
        if (node === h || g.hasEdge(node, h) || g.hasEdge(h, node)) return { ...data, zIndex: 4, forceLabel: true }
        const dimmed = { ...data, color: mixHex(data.color, COLORS.dim, t), label: t > .5 ? null : data.label }
        return t > .5 && data.type === 'image' ? { ...dimmed, image: undefined, type: 'circle' } : dimmed
      },
      edgeReducer: (edge, data) => {
        const h = hoverRef.current, t = dimRef.current
        if (!h || t === 0) return data
        if (g.hasExtremity(edge, h)) return { ...data, color: mixHex(data.color, COLORS.hot, t), size: data.size + (1.2 - data.size) * t, zIndex: 1 }
        return t >= 1 ? { ...data, hidden: true } : { ...data, color: mixHex(data.color, COLORS.bg, t) }
      },
    })
    sigmaRef.current = sigma
    const quick = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const fade = (to, then) => {
      fadeRef.current()
      const from = dimRef.current
      fadeRef.current = tween(quick ? 0 : HOVER_MS * Math.abs(to - from), (p) => { dimRef.current = from + (to - from) * p; sigma.refresh(); if (p === 1) then?.() })
    }
    sigma.on('enterNode', ({ node, event }) => { hoverRef.current = node; setHover({ slug: node, x: event.x, y: event.y }); fade(1) })
    sigma.on('leaveNode', () => { setHover(null); fade(0, () => { hoverRef.current = null; sigma.refresh() }) })
    sigma.on('clickNode', ({ node }) => nodes[node] && setSelected(nodes[node]))
    sigma.on('clickStage', () => setSelected(null))
    const api = {
      flyTo: (id, ratio = .25, duration = 600) => g.hasNode(id) && sigma.getCamera().animate({ ...sigma.getNodeDisplayData(id), ratio }, { duration }),
      overview: (duration = 800) => sigma.getCamera().animate({ x: .5, y: .5, ratio: 1 }, { duration }),
      showPhoto: (k) => { if (g.hasNode(`photo-${k}`)) g.setNodeAttribute(`photo-${k}`, 'size', 20); sigma.refresh() },
      showOverall: () => { g.setNodeAttribute('overall', 'size', 11); sigma.refresh() },
      light: (slug) => { if (g.hasNode(slug)) { g.mergeNodeAttributes(slug, { color: COLORS.hot, size: 8, zIndex: 2 }); sigma.refresh() } },
      select: (slug) => setSelected(nodes[slug] || null),
    }
    onReady?.(api)
    return () => { fadeRef.current(); hoverRef.current = null; dimRef.current = 0; setHover(null); sigma.kill() }
  }, [graph, result, files, urls])

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
      {hover && hover.slug.startsWith('photo-') && (
        <div className="tip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
          <strong>your photo</strong><span>closest to {result.names[result.images[hover.slug.slice(6)].matches[0].slug]}</span>
        </div>
      )}
      {hover && hover.slug === 'overall' && (
        <div className="tip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
          <strong>you</strong><span>all your photos averaged, closest to {result.names[result.overall.matches[0].slug]}</span>
        </div>
      )}
      <Drawer node={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
