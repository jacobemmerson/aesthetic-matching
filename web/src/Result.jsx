import { useEffect, useState } from 'react'
import Graph from './Graph.jsx'

export default function Result({ files, result, onReset }) {
  const [graph, setGraph] = useState(null)
  useEffect(() => { fetch('/api/graph').then((r) => r.json()).then(setGraph) }, [])
  const names = result.overall.map((m) => result.names[m.slug]).join(' · ')
  return (
    <main className="result">
      <header className="result-head"><h1>You are {names}</h1><button className="btn ghost" onClick={onReset}>Start over</button></header>
      {graph && <Graph graph={graph} result={result} files={files} />}
    </main>
  )
}
