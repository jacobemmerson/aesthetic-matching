import { useEffect, useRef, useState } from 'react'
import Graphology from 'graphology'
import Sigma from 'sigma'
import { NodeImageProgram } from '@sigma/node-image'

const SCALE = 60
const DIM = '#e6e0d6'

export default function Graph({ result, files }) {
  const el = useRef(null)
  const [graph, setGraph] = useState(null)
  const [selected, setSelected] = useState(null)

  useEffect(() => { fetch('/api/graph').then((r) => r.json()).then(setGraph) }, [])

  useEffect(() => {
    if (!graph || !el.current) return
    const g = new Graphology()
    const hot = new Set(result.images.flatMap((i) => i.matches.slice(0, 3).map((m) => m.slug)))
    const nodes = Object.fromEntries(graph.nodes.map((n) => [n.slug, n]))
    graph.nodes.forEach((n) => g.addNode(n.slug, {
      x: n.x * SCALE, y: n.y * SCALE, label: n.name, size: hot.has(n.slug) ? 9 : 3,
      color: hot.has(n.slug) ? '#c0392b' : '#b8a98f', zIndex: hot.has(n.slug) ? 2 : 0,
    }))
    graph.edges.forEach((e) => { if (!g.hasEdge(e.source, e.target)) g.addEdge(e.source, e.target, { color: DIM, size: 0.5 }) })
    result.images.forEach((img, k) => g.addNode('photo-' + k, {
      x: img.x * SCALE, y: img.y * SCALE, size: 18, type: 'image', image: URL.createObjectURL(files[k]),
      label: 'your photo ' + (k + 1), color: '#fff', zIndex: 3,
    }))
    const sigma = new Sigma(g, el.current, {
      nodeProgramClasses: { image: NodeImageProgram },
      renderLabels: true, labelRenderedSizeThreshold: 8, labelColor: { color: '#333' }, labelFont: 'Georgia',
    })
    sigma.on('clickNode', ({ node }) => setSelected(nodes[node] || null))
    sigma.on('clickStage', () => setSelected(null))
    const first = result.overall[0]?.slug
    if (first) sigma.getCamera().animate({ ...sigma.getNodeDisplayData(first), ratio: 0.35 }, { duration: 800 })
    return () => sigma.kill()
  }, [graph, result, files])

  return (
    <div className="graph-wrap">
      <div className="graph" ref={el} />
      <aside className="panel">
        {selected ? (
          <>
            <h3>{selected.name}</h3>
            {selected.other_names && <p><em>{selected.other_names}</em></p>}
            <p>{selected.description.slice(0, 700)}{selected.description.length > 700 ? '…' : ''}</p>
            <p><a href={selected.wiki_url} target="_blank" rel="noreferrer">Read on the Aesthetics Wiki →</a></p>
          </>
        ) : (
          <>
            <h3>Your map</h3>
            <p>Every dot is an aesthetic; lines are the wiki's "related" links. Red dots are your matches, the photos sit at their blended position. Click a dot to read about it. Scroll to zoom, drag to pan.</p>
          </>
        )}
      </aside>
    </div>
  )
}
