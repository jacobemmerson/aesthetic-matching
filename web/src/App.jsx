import { useEffect, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import Fade from './Fade.jsx'
import Upload from './Upload.jsx'
import Analyzing from './Analyzing.jsx'
import Result from './Result.jsx'
import { acceptFiles } from './lib/files.js'

export default function App() {
  const [phase, setPhase] = useState('upload')
  const [files, setFiles] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [graph, setGraph] = useState(null)
  const [graphError, setGraphError] = useState(false)

  useEffect(() => {
    fetch('/api/graph').then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json() }).then(setGraph).catch(() => setGraphError(true))
  }, [])

  const onAdd = (list) => {
    const { accepted, notice } = acceptFiles(files, [...list])
    setFiles(accepted); setError(notice)
  }
  const onRemove = (i) => setFiles((f) => f.filter((_, k) => k !== i))

  const onAnalyze = async () => {
    setPhase('analyzing'); setError('')
    const body = new FormData()
    files.forEach((f) => body.append('images', f))
    try {
      const r = await fetch('/api/analyze', { method: 'POST', body })
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
      setResult(await r.json()); setPhase('result')
    } catch (e) { setError(e.message || 'Something went wrong'); setPhase('upload') }
  }
  const onReset = () => { setFiles([]); setResult(null); setError(''); setPhase('upload') }

  return (
    <>
      <AnimatePresence mode="wait">
        {phase === 'upload' && <Fade key="upload"><Upload files={files} onAdd={onAdd} onRemove={onRemove} onAnalyze={onAnalyze} error={error} /></Fade>}
        {phase === 'analyzing' && <Fade key="analyzing"><Analyzing files={files} /></Fade>}
        {phase === 'result' && <Fade key="result"><Result files={files} result={result} graph={graph} graphError={graphError} onReset={onReset} /></Fade>}
      </AnimatePresence>
      <footer className={phase === 'result' ? 'over-map' : undefined}>Aesthetic names and descriptions are from the <a href="https://aesthetics.fandom.com">Aesthetics Wiki</a> (CC BY-SA). Matching uses CLIP image embeddings. Your photos are not stored.</footer>
    </>
  )
}
