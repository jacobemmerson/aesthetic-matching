import { useEffect, useRef, useState } from 'react'
import Graphology from 'graphology'
import Sigma from 'sigma'
import { NodeImageProgram } from '@sigma/node-image'
import { drawDiscNodeLabel } from 'sigma/rendering'
import { AnimatePresence } from 'framer-motion'
import Fade from './Fade.jsx'
import { mixHex, tween } from './lib/tween.js'
import { identity, lookAt, multiply, rotateVec, rotationFromDrag, slerpRotation } from './lib/sphere.js'
import EdgeGrowProgram from './lib/edgeGrow.js'

const SCALE = 60
/** Globe colours come from the CSS tokens on the mount point, so they follow the theme. The tint is passed in: App sets the CSS variable in an effect that runs after this one. */
const colorsFrom = (el, tint) => {
  const style = getComputedStyle(el), v = (name) => style.getPropertyValue(name).trim()
  return { node: v('--graph-node'), edge: v('--graph-edge'), bg: v('--graph-fade'), hot: tint || v('--tint'), label: v('--label'), dim: v('--graph-dim'), you: v('--label'), font: v('--font') }  // bg: what far things fade toward, the shaded body rather than the page
}
const HOVER_MS = 360       // hop 1 lights during the first half, hop 2 during the second
const PHOTO_SIZE = 20
const HORIZON = [-0.15, 0.3]  // depth range over which nodes and edges fade toward the back of the sphere
const facing = (z) => Math.min(1, Math.max(0, (z - HORIZON[0]) / (HORIZON[1] - HORIZON[0])))
const BACK = 0.08             // the far side stays this visible, so the wireframe reads as a volume
const visible = (z) => Math.max(BACK, facing(z))
const EYE = 3                 // perspective: eye distance in sphere radii; near nodes spread and grow, the limb bunches
const perspective = (z) => EYE / (EYE - z)
const LIT_BACK = 0.3          // lit paths stay visible on the far side, at this fraction of full strength
const DRAG_THRESHOLD = 3      // px of movement before a press counts as a drag rather than a click
const FRICTION = 0.94         // momentum kept per frame after letting go; stops below MIN_SPIN
const MIN_SPIN = 0.05         // px per frame
// Names near the mouse: fully lit out to LABEL_CORE px, then a smoothstep cliff down to nothing at LABEL_RADIUS; at most LABEL_MAX of them.
const LABEL_CORE = 130
const LABEL_RADIUS = 300
const LABEL_MAX = 12
const LABEL_BOX = [120, 15]   // px: two names closer than this horizontally and vertically would overlap
const nearness = (dist) => { const t = Math.min(1, Math.max(0, (dist - LABEL_CORE) / (LABEL_RADIUS - LABEL_CORE))); return 1 - t * t * (3 - 2 * t) }

/** sigma's label drawer, with a per-node alpha the reducer sets for names near the cursor. */
const drawLabel = (context, data, settings) => {
  if (data.labelAlpha === undefined) return drawDiscNodeLabel(context, data, settings)
  context.save(); context.globalAlpha = data.labelAlpha; drawDiscNodeLabel(context, data, settings); context.restore()
}
const IDLE_SPIN = 0.3         // px per frame while idling with no result

/** The globe. `result` is optional: without one it idles, turning slowly, with no photo nodes. `images[k]` is the blob URL of photo k. */
export default function Graph({ graph, result, images, onReady, onSelect, scheme, tint, photosVisible = true }) {
  const el = useRef(null)
  const sigmaRef = useRef(null)
  const apiRef = useRef(null)
  const hoverRef = useRef(null)   // node under the cursor (kept while the highlight fades back out)
  const pinRef = useRef(null)     // node whose highlight a click froze, so the globe can be turned around it
  const depthRef = useRef({})     // hops from the hovered node, up to 2
  const dimRef = useRef(0)        // 0 = nothing highlighted, 1 = fully crawled out
  const cursorRef = useRef(null)  // mouse position over the globe, in container px, for the proximity labels
  const nearRef = useRef({})      // slug -> label alpha for the nodes nearest the cursor, recomputed once per frame
  const fadeRef = useRef(() => {})
  const [hover, setHover] = useState(null)      // { slug, x, y }
  const [webglLost, setWebglLost] = useState(false)
  const nodes = Object.fromEntries(graph.nodes.map((n) => [n.slug, n]))
  const hot = new Set(result ? result.aesthetics.map((a) => a.slug) : [])
  const litAtStart = photosVisible ? hot : new Set()  // reveal lights matches via api.light

  useEffect(() => {
    const COLORS = colorsFrom(el.current, tint)
    const g = new Graphology()
    const vec = {}  // node id -> unit vector on the sphere
    graph.nodes.forEach((n) => { vec[n.slug] = [n.x, n.y, n.z]; g.addNode(n.slug, { x: 0, y: 0, depth: 1, label: n.name, size: litAtStart.has(n.slug) ? 8 : 3, color: litAtStart.has(n.slug) ? COLORS.hot : COLORS.node, zIndex: litAtStart.has(n.slug) ? 2 : 0 }) })
    graph.edges.forEach((e) => { if (g.hasNode(e.source) && g.hasNode(e.target) && !g.hasEdge(e.source, e.target)) g.addEdge(e.source, e.target, { color: COLORS.edge, size: .6 }) })
    result?.images.forEach((img, k) => {
      const image = images?.[k]
      if (image) { vec[`photo-${k}`] = [img.x, img.y, img.z]; g.addNode(`photo-${k}`, { x: 0, y: 0, depth: 1, size: photosVisible ? PHOTO_SIZE : 0, type: 'image', image, color: COLORS.hot, zIndex: 3 }) }
    })
    if (result) { vec.overall = [result.overall.x, result.overall.y, result.overall.z]; g.addNode('overall', { x: 0, y: 0, depth: 1, size: photosVisible ? 11 : 0, label: 'You', color: COLORS.you, zIndex: 3 }) }

    const hops = (from) => {  // BFS to two hops
      const depth = { [from]: 0 }
      let frontier = [from]
      for (let d = 1; d <= 2; d++) frontier = frontier.flatMap((n) => g.neighbors(n).filter((m) => depth[m] === undefined && (depth[m] = d)))
      if (from === 'overall') result?.images.forEach((_, k) => { depth[`photo-${k}`] = 1 })  // the photos are You's neighbours
      return depth
    }
    let R = identity()
    const nearLabels = () => {  // the LABEL_MAX nearest front-facing aesthetics to the cursor, with their alphas
      const c = cursorRef.current
      if (!c) { nearRef.current = {}; return }
      const near = []
      g.forEachNode((id, a) => {
        if (a.type === 'image' || id === 'overall' || facing(a.depth) < .5) return
        const v = sigma.graphToViewport({ x: a.x, y: a.y }), dist = Math.hypot(v.x - c.x, v.y - c.y)
        if (dist < LABEL_RADIUS) near.push([id, dist, v])
      })
      near.sort((p, q) => p[1] - q[1])
      const kept = []  // nearest first; a name whose box would land on an already kept one is skipped (forced labels bypass sigma's own collision checks)
      for (const [id, dist, v] of near) {
        if (kept.length === LABEL_MAX) break
        if (!kept.some((k) => Math.abs(k.v.y - v.y) < LABEL_BOX[1] && Math.abs(k.v.x - v.x) < LABEL_BOX[0])) kept.push({ id, dist, v })
      }
      nearRef.current = Object.fromEntries(kept.map(({ id, dist }) => [id, nearness(dist)]))
    }
    const project = () => {
      g.forEachNode((id) => { const [x, y, z] = rotateVec(R, vec[id]); const s = perspective(z); g.mergeNodeAttributes(id, { x: x * s * SCALE, y: y * s * SCALE, depth: z, persp: s }) })
      nearLabels(); sigma.refresh()
    }

    const sigma = new Sigma(g, el.current, {
      nodeProgramClasses: { image: NodeImageProgram }, edgeProgramClasses: { line: EdgeGrowProgram }, renderLabels: true, labelRenderedSizeThreshold: 7,
      labelColor: { color: COLORS.label }, labelFont: COLORS.font, labelSize: 12, zIndex: true, defaultDrawNodeHover: drawDiscNodeLabel, defaultDrawNodeLabel: drawLabel,
      enableCameraPanning: false, enableCameraRotation: false, minCameraRatio: .35, maxCameraRatio: 1.1, stagePadding: 8,
      nodeReducer: (node, data) => {
        const h = hoverRef.current, t = dimRef.current, d = depthRef.current[node]
        const lit = h && t > 0 && d !== undefined
        const f = lit ? Math.max(visible(data.depth), LIT_BACK) : visible(data.depth)  // lit paths show through the far side
        // fade toward the horizon: colour for dots, size for photos (textures can't be tinted); perspective scales everything
        const toward = (d) => ({ ...d, color: mixHex(d.color, COLORS.bg, 1 - f), size: d.size * data.persp * (d.type === 'image' ? f : .7 + .3 * f), label: f < .5 ? null : d.label })
        if (!lit) {
          const base = hot.has(node) && f >= .5 && t === 0 ? { ...toward(data), forceLabel: true } : toward(data)  // verdict nodes keep their name
          const alpha = h ? undefined : nearRef.current[node]
          if (alpha === undefined) return base
          return { ...base, forceLabel: true, labelAlpha: Math.max(base.forceLabel ? 1 : 0, alpha) }  // names fade in toward the cursor
        }
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
        const faceOf = (n) => visible(g.getNodeAttribute(n, 'depth'))
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
    sigma.setCustomBBox({ x: [-SCALE * 1.08, SCALE * 1.08], y: [-SCALE * 1.08, SCALE * 1.08] })  // frame the whole sphere, with room for perspective to push near-limb nodes out
    project()
    const resizer = new ResizeObserver(() => sigma.resize())  // sigma only watches the window, not its container
    resizer.observe(el.current)
    const camera = sigma.getCamera()
    camera.on('updated', () => { if (camera.x !== .5 || camera.y !== .5) camera.setState({ x: .5, y: .5 }) })  // zoom about the centre only

    const quick = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const fade = (to, then) => {
      fadeRef.current()
      const from = dimRef.current
      fadeRef.current = tween(quick ? 0 : HOVER_MS * Math.abs(to - from), (p) => { dimRef.current = from + (to - from) * p; sigma.refresh(); if (p === 1) then?.() })
    }
    let pinned = photosVisible  // photos stay up while the reveal is showing them
    const sizePhotos = (size) => { result?.images.forEach((_, k) => g.hasNode(`photo-${k}`) && g.setNodeAttribute(`photo-${k}`, 'size', size)); sigma.refresh() }
    const focus = (node) => { hoverRef.current = node; depthRef.current = hops(node); fade(1); if (node === 'overall') sizePhotos(PHOTO_SIZE) }
    const unfocus = () => { fade(0, () => { hoverRef.current = null; sigma.refresh() }); if (!pinned) sizePhotos(0) }
    sigma.on('enterNode', ({ node, event }) => { setHover({ slug: node, x: event.x, y: event.y }); if (!pinRef.current) focus(node) })
    sigma.on('leaveNode', () => { setHover(null); if (!pinRef.current) unfocus() })
    sigma.on('clickNode', ({ node }) => {  // click freezes the lit paths; clicking the same node or the stage lets go
      pinRef.current = pinRef.current === node ? null : node
      if (pinRef.current) focus(node); else unfocus()
      if (nodes[node]) onSelect?.(nodes[node])
    })
    sigma.on('clickStage', () => { if (dragged) return; onSelect?.(null); if (pinRef.current) { pinRef.current = null; unfocus() } })  // a drag ending on the stage is not a click

    // drag anywhere spins the sphere (pointer events cover mouse and touch)
    // No pointer capture: that would steal the mouse-up and click from sigma's own canvas.
    let drag = null, dragged = false, velocity = [0, 0], lastMove = 0, coast = null
    const container = el.current
    // Safari sometimes revokes every WebGL context (seen on macOS 18.1); sigma can't recover, so say so instead of showing black
    const lost = () => setWebglLost(true)
    container.addEventListener('webglcontextlost', lost, true)  // the event doesn't bubble; capture still sees it
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

    // names near the mouse fade in (no cursor on touch, so touch is ignored); one refresh per frame at most
    let cursorRaf = null
    const cursorMove = (e) => {
      if (e.pointerType !== 'mouse') return
      const r = container.getBoundingClientRect()
      cursorRef.current = { x: e.clientX - r.left, y: e.clientY - r.top }
      cursorRaf ??= requestAnimationFrame(() => { cursorRaf = null; nearLabels(); sigma.refresh() })
    }
    const cursorLeave = () => { cursorRef.current = null; nearRef.current = {}; sigma.refresh() }
    container.addEventListener('pointermove', cursorMove); container.addEventListener('pointerleave', cursorLeave)

    // With no result the globe is scenery: keep it turning, except while the hand or the cursor is on it
    let idleRaf = null
    const idleStep = () => { if (!drag && !coast && !hoverRef.current && !spin.flying) turn(IDLE_SPIN, 0); idleRaf = requestAnimationFrame(idleStep) }
    if (!result && !quick) idleRaf = requestAnimationFrame(idleStep)

    const spin = { cancel: null, flying: false }
    const turnTo = (id, duration) => {
      spin.cancel?.(); stopCoast(); spin.flying = true
      const from = R, to = lookAt(vec[id])
      spin.cancel = tween(quick ? 0 : duration, (p) => { R = slerpRotation(from, to, p); project(); if (p === 1) spin.flying = false })
    }
    const api = {
      flyTo: (id, ratio = .25, duration = 600) => { if (!g.hasNode(id)) return; turnTo(id, duration); camera.animate({ x: .5, y: .5, ratio }, { duration: quick ? 0 : duration }) },
      overview: (duration = 800) => camera.animate({ x: .5, y: .5, ratio: 1 }, { duration }),
      showPhoto: (k) => { pinned = true; if (g.hasNode(`photo-${k}`)) g.setNodeAttribute(`photo-${k}`, 'size', PHOTO_SIZE); sigma.refresh() },
      hidePhotos: () => { pinned = false; sizePhotos(0) },
      showOverall: () => { if (g.hasNode('overall')) { g.setNodeAttribute('overall', 'size', 11); sigma.refresh() } },
      light: (slug) => { if (g.hasNode(slug)) { g.mergeNodeAttributes(slug, { color: COLORS.hot, size: 8, zIndex: 2 }); sigma.refresh() } },
      addPhoto: (k, pos, image, slug) => {  // while analyzing: the photo lands on the globe, its best match lights, the globe turns to it
        const id = `photo-${k}`
        if (g.hasNode(id) || !image) return
        vec[id] = [pos.x, pos.y, pos.z]
        g.addNode(id, { x: 0, y: 0, depth: 1, size: PHOTO_SIZE, type: 'image', image, color: COLORS.hot, zIndex: 3 })
        pinned = true
        api.light(slug); project(); turnTo(id, 600)
      },
      select: (slug) => onSelect?.(nodes[slug] || null),
      locate: (id) => {  // where a node is on screen, in page pixels, and whether it faces the viewer
        if (!g.hasNode(id)) return null
        const { x, y, depth } = g.getNodeAttributes(id), v = sigma.graphToViewport({ x, y }), r = container.getBoundingClientRect()
        return { x: v.x + r.left, y: v.y + r.top, front: facing(depth) >= .5 }
      },
    }
    apiRef.current = api
    onReady?.(api)
    return () => {
      fadeRef.current(); spin.cancel?.(); stopCoast(); cancelAnimationFrame(idleRaf); resizer.disconnect(); hoverRef.current = null; pinRef.current = null; dimRef.current = 0; setHover(null)
      container.removeEventListener('pointerdown', down); window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up); window.removeEventListener('pointercancel', up)
      container.removeEventListener('webglcontextlost', lost, true)
      container.removeEventListener('pointermove', cursorMove); container.removeEventListener('pointerleave', cursorLeave); cancelAnimationFrame(cursorRaf); cursorRef.current = null; nearRef.current = {}
      sigma.kill()
    }
  }, [graph, result, images, scheme, tint])  // theme and tint changes rebuild; Result replays the reveal state via onReady

  return (
    <div className="graph-shell">
      <div className="graph" ref={el} />
      <AnimatePresence>
        {webglLost && <Fade as="p" key="webgl" className="notice graph-notice">Your browser dropped WebGL, so the map can't draw. Safari on macOS does this; try Chrome or Firefox.</Fade>}
        {hover && nodes[hover.slug] && (
          <Fade key="tip-node" duration={.15} className="tip material-thick" style={{ left: hover.x + 14, top: hover.y + 14 }}>
            <strong>{nodes[hover.slug].name}</strong><span>{nodes[hover.slug].description.split(/(?<=\.)\s/)[0]}</span>
          </Fade>
        )}
        {hover && result && hover.slug.startsWith('photo-') && (
          <Fade key="tip-photo" duration={.15} className="tip material-thick" style={{ left: hover.x + 14, top: hover.y + 14 }}>
            <strong>Your photo</strong><span>closest to {result.names[result.images[hover.slug.slice(6)].matches[0].slug]}</span>
          </Fade>
        )}
        {hover && result && hover.slug === 'overall' && (
          <Fade key="tip-you" duration={.15} className="tip material-thick" style={{ left: hover.x + 14, top: hover.y + 14 }}>
            <strong>You</strong><span>Your photos, averaged. Closest to {result.names[result.overall.matches[0].slug]}.</span>
          </Fade>
        )}
      </AnimatePresence>
    </div>
  )
}
