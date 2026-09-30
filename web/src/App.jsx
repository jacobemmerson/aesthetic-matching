import { useState } from 'react'
import Upload from './Upload.jsx'
import Analyzing from './Analyzing.jsx'
import Result from './Result.jsx'
import { acceptFiles } from './lib/files.js'

export default function App() {
  const [phase, setPhase] = useState('upload')
  const [files, setFiles] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

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
      {phase === 'upload' && <Upload files={files} onAdd={onAdd} onRemove={onRemove} onAnalyze={onAnalyze} error={error} />}
      {phase === 'analyzing' && <Analyzing files={files} />}
      {phase === 'result' && <Result files={files} result={result} onReset={onReset} />}
      <footer>Aesthetic names and descriptions are from the <a href="https://aesthetics.fandom.com">Aesthetics Wiki</a> (CC BY-SA). Matching uses CLIP image embeddings. Your photos are not stored.</footer>
    </>
  )
}
