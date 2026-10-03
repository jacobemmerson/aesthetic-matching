import { useEffect, useRef, useState } from 'react'
import Graphology from 'graphology'
import Sigma from 'sigma'
import { NodeImageProgram } from '@sigma/node-image'
import { drawDiscNodeLabel } from 'sigma/rendering'
import { useObjectUrls } from './lib/objectUrls.js'
import Drawer from './Drawer.jsx'
import { mixHex, tween } from './lib/tween.js'
import { identity, lookAt, multiply, rotateVec, rotationFromDrag, slerpRotation } from './lib/sphere.js'
import EdgeGrowProgram from './lib/edgeGrow.js'

const SCALE = 60
const COLORS = { node: '#4a4740', edge: '#1e1e23', bg: '#0b0b0d', hot: '#ff4d6d', label: '#f2efe9', dim: '#1c1c20', you: '#f2efe9' }
const HOVER_MS = 360       // hop 1 lights during the first half, hop 2 during the second
const PHOTO_SIZE = 20
const HORIZON = [-0.15, 0.3]  // depth range over which nodes and edges fade out toward the back of the sphere
const facing = (z) => Math.min(1, Math.max(0, (z - HORIZON[0]) / (HORIZON[1] - HORIZON[0])))
const LIT_BACK = 0.3          // lit paths stay visible on the far side, at this fraction of full strength
const DRAG_THRESHOLD = 3      // px of movement before a press counts as a drag rather than a click
const FRICTION = 0.94         // momentum kept per frame after letting go; stops below MIN_SPIN
const MIN_SPIN = 0.05         // px per frame

export default function Graph({ graph, result, files, onReady, photosVisible = true }) {
  const el = useRef(null)
  const sigmaRef = useRef(null)
  const apiRef = useRef(null)
  const hoverRef = useRef(null)   // node under the cursor (kept while the highlight fades back out)
  const pinRef = useRef(null)     // node whose highlight a click froze, so the globe can be turned around it
  const depthRef = useRef({})     // hops from the hovered node, up to 2
  const dimRef = useRef(0)        // 0 = nothing highlighted, 1 = fully crawled out
  const fadeRef = useRef(() => {})
  const urls = useObjectUrls(files)
  const [hover, setHover] = useState(null)      // { slug, x, y }
  const [webglLost, setWebglLost] = useState(false)
  const [selected, setSelected] = useState(null) // node object
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

    const hops = (from) => {  // BFS to two hops
      const depth = { [from]: 0 }
      let frontier = [from]
      for (let d = 1; d <= 2; d++) frontier = frontier.flatMap((n) => g.neighbors(n).filter((m) => depth[m] === undefined && (depth[m] = d)))
      if (from === 'overall') result.images.forEach((_, k) => { depth[`photo-${k}`] = 1 })  // the photos are You's neighbours
      return depth
    }
    let R = identity()
    const project = () => {
      g.forEachNode((id) => { const [x, y, z] = rotateVec(R, vec[id]); g.mergeNodeAttributes(id, { x: x * SCALE, y: y * SCALE, depth: z }) })
      sigma.refresh()
    }

    const sigma = new Sigma(g, el.current, {
      nodeProgramClasses: { image: NodeImageProgram }, edgeProgramClasses: { line: EdgeGrowProgram }, renderLabels: true, labelRenderedSizeThreshold: 7,
      labelColor: { color: COLORS.label }, labelFont: getComputedStyle(document.documentElement).getPropertyValue('--ui').trim(), labelSize: 12, zIndex: true, defaultDrawNodeHover: drawDiscNodeLabel,
      enableCameraPanning: false, enableCameraRotation: false, minCameraRatio: .35, maxCameraRatio: 1.1, stagePadding: 8,
      nodeReducer: (node, data) => {
        const h = hoverRef.current, t = dimRef.current, d = depthRef.current[node]
        const lit = h && t > 0 && d !== undefined
        const f = lit ? Math.max(facing(data.depth), LIT_BACK) : facing(data.depth)  // lit paths show through the far side
        if (f === 0) return { ...data, hidden: true }
        // fade toward the horizon: colour for dots, size for photos (textures can't be tinted)
        const toward = (d) => ({ ...d, color: mixHex(d.color, COLORS.bg, 1 - f), size: d.size * (d.type === 'image' ? f : .7 + .3 * f), label: f < .5 ? null : d.label })
        if (!lit) return hot.has(node) && f >= .5 && t === 0 ? { ...toward(data), forceLabel: true } : toward(data)  // verdict nodes keep their name
        if (d === 0) return { ...toward(data), zIndex: 4, forceLabel: true }
        // every lit node facing the viewer shows its name once its hop has lit
        if (d === 1) { const k = Math.min(1, 2 * t); return { ...toward({ ...data, color: mixHex(data.color, COLORS.hot, k) }), zIndex: 3, forceLabel: k > .5 && f >= .5 } }
        if (d === 2) { const k = .6 * Math.max(0, 2 * t - 1); return { ...toward({ ...data, color: mixHex(data.color, COLORS.hot, k) }), zIndex: 2, forceLabel: k > .3 && f >= .5 } }
        const dimmed = toward({ ...data, color: mixHex(data.color, COLORS.dim, t) })
        if (t > .5) dimmed.label = null
        return t > .5 && data.size > 8 ? { ...dimmed, image: undefined, type: 'circle', size: 3 } : dimmed  // photos and You shrink to dots
      },
      edgeReducer: (edge, data) => {
        const [sa, sb] = g.extremities(edge)
        const h = hoverRef.current, t = dimRef.current
        const [a, b] = [depthRef.current[sa], depthRef.current[sb]]
        const hop = h && t > 0 && a !== undefined && b !== undefined && Math.abs(a - b) === 1 ? Math.max(a, b) : 0
        const faceOf = (n) => facing(g.getNodeAttribute(n, 'depth'))
        const f = hop ? Math.max(Math.min(faceOf(sa), faceOf(sb)), LIT_BACK) : Math.min(faceOf(sa), faceOf(sb))
        const toward = (d) => ({ ...d, color: mixHex(d.color, COLORS.bg, 1 - f) })
        if (!h || t === 0) return toward(data)
        if (hop) {  // the highlight travels out from the nearer end as its hop's clock runs
          const clock = hop === 1 ? Math.min(1, 2 * t) : Math.max(0, 2 * t - 1), k = hop === 1 ? clock : .6 * clock
          return { ...toward({ ...data, color: mixHex(data.color, COLORS.hot, k) }), size: data.size + (1.2 - data.size) * k, zIndex: 1, grow: clock, growFrom: a < b ? 'source' : 'target' }
        }
        return t >= 1 ? { ...data, hidden: true } : toward({ ...data, color: mixHex(data.color, COLORS.bg, t) })
      },
    })
    sigmaRef.current = sigma
    sigma.setCustomBBox({ x: [-SCALE, SCALE], y: [-SCALE, SCALE] })  // frame the whole sphere, not whichever nodes face front
    project()
    const resizer = new ResizeObserver(() => sigma.resize())  // sigma only watches the window, not its container
    resizer.observe(el.current)
    // Safari sometimes revokes every WebGL context (seen on macOS 18.1); sigma can't recover, so say so instead of showing black
    const lost = () => setWebglLost(true)
    el.current.addEventListener('webglcontextlost', lost, true)  // the event doesn't bubble; capture still sees it
    const camera = sigma.getCamera()
    camera.on('updated', () => { if (camera.x !== .5 || camera.y !== .5) camera.setState({ x: .5, y: .5 }) })  // zoom about the centre only

    const quick = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const fade = (to, then) => {
      fadeRef.current()
      const from = dimRef.current
      fadeRef.current = tween(quick ? 0 : HOVER_MS * Math.abs(to - from), (p) => { dimRef.current = from + (to - from) * p; sigma.refresh(); if (p === 1) then?.() })
    }
    let pinned = photosVisible  // photos stay up while the reveal is showing them
    const sizePhotos = (size) => { result.images.forEach((_, k) => g.hasNode(`photo-${k}`) && g.setNodeAttribute(`photo-${k}`, 'size', size)); sigma.refresh() }
    const focus = (node) => { hoverRef.current = node; depthRef.current = hops(node); fade(1); if (node === 'overall') sizePhotos(PHOTO_SIZE) }
    const unfocus = () => { fade(0, () => { hoverRef.current = null; sigma.refresh() }); if (!pinned) sizePhotos(0) }
    sigma.on('enterNode', ({ node, event }) => { setHover({ slug: node, x: event.x, y: event.y }); if (!pinRef.current) focus(node) })
    sigma.on('leaveNode', () => { setHover(null); if (!pinRef.current) unfocus() })
    sigma.on('clickNode', ({ node }) => {  // click freezes the lit paths; clicking the same node or the stage lets go
      pinRef.current = pinRef.current === node ? null : node
      if (pinRef.current) focus(node); else unfocus()
      nodes[node] && setSelected(nodes[node])
    })
    sigma.on('clickStage', () => { if (dragged) return; setSelected(null); if (pinRef.current) { pinRef.current = null; unfocus() } })  // a drag ending on the stage is not a click

    // drag anywhere spins the sphere (pointer events cover mouse and touch)
    // No pointer capture: that would steal the mouse-up and click from sigma's own canvas.
    let drag = null, dragged = false, velocity = [0, 0], lastMove = 0, coast = null
    const container = el.current
    const radiusPx = () => { const o = sigma.graphToViewport({ x: 0, y: 0 }), r = sigma.graphToViewport({ x: SCALE, y: 0 }); return Math.hypot(r.x - o.x, r.y - o.y) }
    const turn = (dx, dy) => { R = multiply(rotationFromDrag(dx, dy, 1 / radiusPx()), R); project() }  // one pixel per pixel of on-screen radius, so the pointer tracks
    const stopCoast = () => { cancelAnimationFrame(coast); coast = null }
    const down = (e) => { if (e.button === 0 || e.pointerType !== 'mouse') { stopCoast(); drag = [e.clientX, e.clientY]; dragged = false; velocity = [0, 0] } }
    const move = (e) => {
      if (!drag) return
      const dx = e.clientX - drag[0], dy = e.clientY - drag[1]
      if (!dragged && Math.hypot(dx, dy) < DRAG_THRESHOLD) return
      dragged = true; spin.cancel?.(); turn(dx, dy); drag = [e.clientX, e.clientY]
      const now = performance.now(), dt = Math.max(1, now - lastMove); lastMove = now
      velocity = [dx / dt * 16, dy / dt * 16]  // px per frame at 60 Hz
    }
    const up = () => {  // keep spinning with what the hand left, decaying each frame
      if (!drag) return
      drag = null
      if (quick || performance.now() - lastMove > 80) return  // a pause before release means a deliberate stop
      const step = () => {
        velocity = velocity.map((v) => v * FRICTION)
        if (Math.hypot(...velocity) < MIN_SPIN) { coast = null; return }
        turn(velocity[0], velocity[1]); coast = requestAnimationFrame(step)
      }
      coast = requestAnimationFrame(step)
    }
    container.addEventListener('pointerdown', down); window.addEventListener('pointermove', move); window.addEventListener('pointerup', up); window.addEventListener('pointercancel', up)

    const spin = { cancel: null }
    const turnTo = (id, duration) => {
      spin.cancel?.(); stopCoast()
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
      fadeRef.current(); spin.cancel?.(); stopCoast(); resizer.disconnect(); hoverRef.current = null; pinRef.current = null; dimRef.current = 0; setHover(null)
      container.removeEventListener('pointerdown', down); window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); window.removeEventListener('pointercancel', up)
      el.current?.removeEventListener('webglcontextlost', lost, true)
      sigma.kill()
    }
  }, [graph, result, files, urls])

  return (
    <div className="graph-shell">
      <div className="graph" ref={el} />
      {webglLost && <p className="notice graph-notice">Your browser dropped WebGL, so the map can't draw. Safari on macOS does this; try Chrome or Firefox.</p>}
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
