import { useState } from 'react'
import Graph from './Graph.jsx'

const MAX = 10

export default function App() {
  const [files, setFiles] = useState([])
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [over, setOver] = useState(false)

  const add = (list) => {
    const imgs = [...list].filter((f) => f.type.startsWith('image/') && f.size <= 5e6)
    setFiles((cur) => [...cur, ...imgs].slice(0, MAX))
    setResult(null)
  }

  const analyze = async () => {
    setBusy(true); setError('')
    const body = new FormData()
    files.forEach((f) => body.append('images', f))
    try {
      const r = await fetch('/api/analyze', { method: 'POST', body })
      if (!r.ok) throw new Error((await r.json()).detail || r.statusText)
      setResult(await r.json())
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const names = result ? Object.fromEntries(result.images.map((i, k) => [k, i])) : {}

  return (
    <main>
      <h1>What's your aesthetic?</h1>
      <p className="sub">Upload a few photos from your life. See where you land on the map of every internet aesthetic.</p>

      <label className={'drop' + (over ? ' over' : '')}
        onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); add(e.dataTransfer.files) }}>
        Drop up to {MAX} photos here, or click to choose (JPEG/PNG, under 5 MB each)
        <input type="file" accept="image/*" multiple hidden onChange={(e) => add(e.target.files)} />
      </label>

      {files.length > 0 && (
        <div className="thumbs">
          {files.map((f, k) => (
            <figure key={k}>
              <img src={URL.createObjectURL(f)} alt="" />
              {names[k] && <figcaption>{names[k].matches.slice(0, 3).map((m) => <span className="chip" key={m.slug}>{result.names[m.slug]}</span>)}</figcaption>}
            </figure>
          ))}
        </div>
      )}

      {files.length > 0 && !result && <button onClick={analyze} disabled={busy}>{busy ? 'Analyzing…' : 'Find my aesthetic'}</button>}
      {error && <p className="err">{error}</p>}

      {result && (
        <>
          <div className="verdict">Your aesthetic: <strong>{result.overall.map((m) => result.names[m.slug]).join(' · ')}</strong></div>
          <Graph result={result} files={files} />
          <p><button onClick={() => { setFiles([]); setResult(null) }}>Start over</button></p>
        </>
      )}
      <footer>Aesthetic names and descriptions are from the <a href="https://aesthetics.fandom.com">Aesthetics Wiki</a> (CC BY-SA). Matching uses CLIP image embeddings. Your photos are not stored.</footer>
    </main>
  )
}
