import { useEffect, useRef, useState } from 'react'
import Graphology from 'graphology'
import Sigma from 'sigma'
import { NodeImageProgram } from '@sigma/node-image'
import { drawDiscNodeLabel } from 'sigma/rendering'
import { useObjectUrls } from './lib/objectUrls.js'
import Drawer from './Drawer.jsx'
import { searchNodes } from './lib/search.js'
import { mixHex, tween } from './lib/tween.js'
import { identity, lookAt, multiply, rotateVec, rotationFromDrag, slerpRotation } from './lib/sphere.js'

const SCALE = 60
const DRAG_SPEED = 0.006   // radians per pixel
const COLORS = { node: '#4a4740', edge: '#1e1e23', bg: '#0b0b0d', hot: '#ff4d6d', label: '#f2efe9', dim: '#1c1c20', you: '#f2efe9' }
const HOVER_MS = 360       // hop 1 lights during the first half, hop 2 during the second
const PHOTO_SIZE = 20
const HORIZON = [-0.15, 0.3]  // depth range over which nodes and edges fade out toward the back of the sphere
const facing = (z) => Math.min(1, Math.max(0, (z - HORIZON[0]) / (HORIZON[1] - HORIZON[0])))

export default function Graph({ graph, result, files, onReady, photosVisible = true }) {
  const el = useRef(null)
  const sigmaRef = useRef(null)
  const apiRef = useRef(null)
  const hoverRef = useRef(null)   // node under the cursor (kept while the highlight fades back out)
  const depthRef = useRef({})     // hops from the hovered node, up to 2
  const dimRef = useRef(0)        // 0 = nothing highlighted, 1 = fully crawled out
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
    const vec = {}  // node id -> unit vector on the sphere
    graph.nodes.forEach((n) => { vec[n.slug] = [n.x, n.y, n.z]; g.addNode(n.slug, { x: 0, y: 0, depth: 1, label: n.name, size: litAtStart.has(n.slug) ? 8 : 3, color: litAtStart.has(n.slug) ? COLORS.hot : COLORS.node, zIndex: litAtStart.has(n.slug) ? 2 : 0 }) })
    graph.edges.forEach((e) => { if (g.hasNode(e.source) && g.hasNode(e.target) && !g.hasEdge(e.source, e.target)) g.addEdge(e.source, e.target, { color: COLORS.edge, size: .6 }) })
    result.images.forEach((img, k) => {
      const image = urls.get(files[k])
      if (image) { vec[`photo-${k}`] = [img.x, img.y, img.z]; g.addNode(`photo-${k}`, { x: 0, y: 0, depth: 1, size: photosVisible ? PHOTO_SIZE : 0, type: 'image', image, color: COLORS.hot, zIndex: 3 }) }
    })
    vec.overall = [result.overall.x, result.overall.y, result.overall.z]
    g.addNode('overall', { x: 0, y: 0, depth: 1, size: photosVisible ? 11 : 0, label: 'You', color: COLORS.you, zIndex: 3 })

    let R = identity()
    const project = () => {
      g.forEachNode((id) => { const [x, y, z] = rotateVec(R, vec[id]); g.mergeNodeAttributes(id, { x: x * SCALE, y: y * SCALE, depth: z }) })
      sigma.refresh()
    }

    const sigma = new Sigma(g, el.current, {
      nodeProgramClasses: { image: NodeImageProgram }, renderLabels: true, labelRenderedSizeThreshold: 7,
      labelColor: { color: COLORS.label }, labelFont: 'Inter', labelSize: 12, zIndex: true, defaultDrawNodeHover: drawDiscNodeLabel,
      enableCameraPanning: false, enableCameraRotation: false, minCameraRatio: .35, maxCameraRatio: 1.1,
      nodeReducer: (node, data) => {
        const f = facing(data.depth)
        if (f === 0) return { ...data, hidden: true }
        // fade toward the horizon: colour for dots, size for photos (textures can't be tinted)
        const toward = (d) => ({ ...d, color: mixHex(d.color, COLORS.bg, 1 - f), size: d.size * (d.type === 'image' ? f : .7 + .3 * f), label: f < .5 ? null : d.label })
        const h = hoverRef.current, t = dimRef.current, d = depthRef.current[node]
        if (!h || t === 0) return toward(data)
        if (d === 0) return { ...toward(data), zIndex: 4, forceLabel: true }
        if (d === 1) { const k = Math.min(1, 2 * t); return { ...toward({ ...data, color: mixHex(data.color, COLORS.hot, k) }), zIndex: 3, forceLabel: k > .5 && f >= .5 } }
        if (d === 2) { const k = .6 * Math.max(0, 2 * t - 1); return { ...toward({ ...data, color: mixHex(data.color, COLORS.hot, k) }), zIndex: 2 } }
        const dimmed = toward({ ...data, color: mixHex(data.color, COLORS.dim, t) })
        if (t > .5) dimmed.label = null
        return t > .5 && data.size > 8 ? { ...dimmed, image: undefined, type: 'circle', size: 3 } : dimmed  // photos and You shrink to dots
      },
      edgeReducer: (edge, data) => {
        const [sa, sb] = g.extremities(edge)
        const f = Math.min(facing(g.getNodeAttribute(sa, 'depth')), facing(g.getNodeAttribute(sb, 'depth')))
        const toward = (d) => ({ ...d, color: mixHex(d.color, COLORS.bg, 1 - f) })
        const h = hoverRef.current, t = dimRef.current
        if (!h || t === 0) return toward(data)
        const [a, b] = [depthRef.current[sa], depthRef.current[sb]]
        const hop = a !== undefined && b !== undefined && Math.abs(a - b) === 1 ? Math.max(a, b) : 0
        if (hop) { const k = hop === 1 ? Math.min(1, 2 * t) : .6 * Math.max(0, 2 * t - 1); return { ...toward({ ...data, color: mixHex(data.color, COLORS.hot, k) }), size: data.size + (1.2 - data.size) * k, zIndex: 1 } }
        return t >= 1 ? { ...data, hidden: true } : toward({ ...data, color: mixHex(data.color, COLORS.bg, t) })
      },
    })
    sigmaRef.current = sigma
    sigma.setCustomBBox({ x: [-SCALE, SCALE], y: [-SCALE, SCALE] })  // frame the whole sphere, not whichever nodes face front
    project()
    const resizer = new ResizeObserver(() => sigma.resize())  // sigma only watches the window, not its container
    resizer.observe(el.current)
    const camera = sigma.getCamera()
    camera.on('updated', () => { if (camera.x !== .5 || camera.y !== .5) camera.setState({ x: .5, y: .5 }) })  // zoom about the centre only

    const quick = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const hops = (from) => {  // BFS to two hops
      const depth = { [from]: 0 }
      let frontier = [from]
      for (let d = 1; d <= 2; d++) frontier = frontier.flatMap((n) => g.neighbors(n).filter((m) => depth[m] === undefined && (depth[m] = d)))
      if (from === 'overall') result.images.forEach((_, k) => { depth[`photo-${k}`] = 1 })  // the photos are You's neighbours
      return depth
    }
    const fade = (to, then) => {
      fadeRef.current()
      const from = dimRef.current
      fadeRef.current = tween(quick ? 0 : HOVER_MS * Math.abs(to - from), (p) => { dimRef.current = from + (to - from) * p; sigma.refresh(); if (p === 1) then?.() })
    }
    let pinned = photosVisible  // photos stay up while the reveal is showing them
    const sizePhotos = (size) => { result.images.forEach((_, k) => g.hasNode(`photo-${k}`) && g.setNodeAttribute(`photo-${k}`, 'size', size)); sigma.refresh() }
    sigma.on('enterNode', ({ node, event }) => {
      hoverRef.current = node; depthRef.current = hops(node); setHover({ slug: node, x: event.x, y: event.y }); fade(1)
      if (node === 'overall') sizePhotos(PHOTO_SIZE)
    })
    sigma.on('leaveNode', () => { setHover(null); fade(0, () => { hoverRef.current = null; sigma.refresh() }); if (!pinned) sizePhotos(0) })
    sigma.on('clickNode', ({ node }) => nodes[node] && setSelected(nodes[node]))
    sigma.on('clickStage', () => setSelected(null))

    // drag anywhere spins the sphere (pointer events cover mouse and touch)
    let drag = null
    const container = el.current
    const down = (e) => { if (e.button === 0 || e.pointerType !== 'mouse') { drag = [e.clientX, e.clientY]; container.setPointerCapture?.(e.pointerId) } }
    const move = (e) => { if (!drag) return; spin.cancel?.(); R = multiply(rotationFromDrag(e.clientX - drag[0], e.clientY - drag[1], DRAG_SPEED), R); drag = [e.clientX, e.clientY]; project() }
    const up = () => { drag = null }
    container.addEventListener('pointerdown', down); container.addEventListener('pointermove', move); container.addEventListener('pointerup', up); container.addEventListener('pointercancel', up)

    const spin = { cancel: null }
    const turnTo = (id, duration) => {
      spin.cancel?.()
      const from = R, to = lookAt(vec[id])
      spin.cancel = tween(quick ? 0 : duration, (p) => { R = slerpRotation(from, to, p); project() })
    }
    const api = {
      flyTo: (id, ratio = .25, duration = 600) => { if (!g.hasNode(id)) return; turnTo(id, duration); camera.animate({ x: .5, y: .5, ratio }, { duration: quick ? 0 : duration }) },
      overview: (duration = 800) => camera.animate({ x: .5, y: .5, ratio: 1 }, { duration }),
      showPhoto: (k) => { pinned = true; if (g.hasNode(`photo-${k}`)) g.setNodeAttribute(`photo-${k}`, 'size', PHOTO_SIZE); sigma.refresh() },
      hidePhotos: () => { pinned = false; sizePhotos(0) },
      showOverall: () => { g.setNodeAttribute('overall', 'size', 11); sigma.refresh() },
      light: (slug) => { if (g.hasNode(slug)) { g.mergeNodeAttributes(slug, { color: COLORS.hot, size: 8, zIndex: 2 }); sigma.refresh() } },
      select: (slug) => setSelected(nodes[slug] || null),
    }
    apiRef.current = api
    onReady?.(api)
    return () => {
      fadeRef.current(); spin.cancel?.(); resizer.disconnect(); hoverRef.current = null; dimRef.current = 0; setHover(null)
      container.removeEventListener('pointerdown', down); container.removeEventListener('pointermove', move); container.removeEventListener('pointerup', up); container.removeEventListener('pointercancel', up)
      sigma.kill()
    }
  }, [graph, result, files, urls])

  const hits = searchNodes(graph.nodes, query)
  const pick = (n) => { setQuery(''); apiRef.current?.flyTo(n.slug); setSelected(n) }

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
          <strong>Your photo</strong><span>closest to {result.names[result.images[hover.slug.slice(6)].matches[0].slug]}</span>
        </div>
      )}
      {hover && hover.slug === 'overall' && (
        <div className="tip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
          <strong>You</strong><span>Your photos, averaged. Closest to {result.names[result.overall.matches[0].slug]}.</span>
        </div>
      )}
      <Drawer node={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
