import { useEffect, useRef, useState } from 'react'
import Graphology from 'graphology'
import Sigma from 'sigma'
import { NodeImageProgram } from '@sigma/node-image'
import { useObjectUrls } from './lib/objectUrls.js'
import Drawer from './Drawer.jsx'
import { searchNodes } from './lib/search.js'

const SCALE = 60
const COLORS = { node: '#4a4740', edge: '#1e1e23', hot: '#ff4d6d', label: '#f2efe9', dim: '#1c1c20' }

export default function Graph({ graph, result, files, onReady, photosVisible = true }) {
  const el = useRef(null)
  const sigmaRef = useRef(null)
  const hoverRef = useRef(null)
  const urls = useObjectUrls(files)
  const [hover, setHover] = useState(null)      // { slug, x, y }
  const [selected, setSelected] = useState(null) // node object
  const [query, setQuery] = useState('')
  const nodes = Object.fromEntries(graph.nodes.map((n) => [n.slug, n]))
  const hot = new Set(result.images.map((i) => i.matches[0].slug))

  useEffect(() => {
    const g = new Graphology()
    graph.nodes.forEach((n) => g.addNode(n.slug, { x: n.x * SCALE, y: n.y * SCALE, label: n.name, size: hot.has(n.slug) ? 8 : 3, color: hot.has(n.slug) ? COLORS.hot : COLORS.node, zIndex: hot.has(n.slug) ? 2 : 0 }))
    graph.edges.forEach((e) => { if (g.hasNode(e.source) && g.hasNode(e.target) && !g.hasEdge(e.source, e.target)) g.addEdge(e.source, e.target, { color: COLORS.edge, size: .6 }) })
    result.images.forEach((img, k) => {
      const image = urls.get(files[k])
      if (image) g.addNode(`photo-${k}`, { x: img.x * SCALE, y: img.y * SCALE, size: 20, type: 'image', image, label: `your photo ${k + 1}`, color: COLORS.hot, zIndex: 3, hidden: !photosVisible })
    })

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
    return () => { hoverRef.current = null; setHover(null); sigma.kill() }
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
      <Drawer node={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
