import { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import Fade from './Fade.jsx'
import Graph from './Graph.jsx'
import Sheet from './Sheet.jsx'
import { AnalyzeButton, UploadIntro } from './Upload.jsx'
import PhotoList from './PhotoList.jsx'
import Analyzing from './Analyzing.jsx'
import Result from './Result.jsx'
import NodeDetail from './NodeDetail.jsx'
import Credits from './Credits.jsx'
import { acceptFiles } from './lib/files.js'
import { useObjectUrls } from './lib/objectUrls.js'
import { useColorScheme } from './lib/scheme.js'
import { hueOfFiles, tintHex } from './lib/tint.js'
import { ndjson } from './lib/stream.js'
import { phraseFor } from './lib/loading.js'
import { pacer } from './lib/pace.js'
import { reduced } from './lib/motion.js'

const PACE = 700  // ms between photos landing on the globe, so a fast server still reads as a sequence

const phaseMotion = { initial: { opacity: 0, scale: .98 }, animate: { opacity: 1, scale: 1 }, exit: { opacity: 0, scale: .98 }, transition: { duration: .3 } }

/** One scene: the globe behind, one sheet in front, and the phase only changes what the sheet shows. */
export default function App() {
  const [phase, setPhase] = useState('upload')
  const [files, setFiles] = useState([])
  const [result, setResult] = useState(null)
  const [hue, setHue] = useState(null)   // oklch hue of the photos, tints the result; null = default tint
  const [progress, setProgress] = useState([])  // photo lines shown so far while analyzing
  const [statement, setStatement] = useState(null)  // arrives last, after the result is already on screen
  const [error, setError] = useState('')
  const [graph, setGraph] = useState(null)
  const [graphError, setGraphError] = useState(false)
  const [node, setNode] = useState(null)  // aesthetic shown in the sheet instead of the phase content
  const urls = useObjectUrls(files)  // one blob URL per file, shared by every phase
  const images = useMemo(() => result && files.map((f) => urls.get(f)), [result, urls])  // the globe only gets photos once there is a result, so adding photos doesn't rebuild it
  const scheme = useColorScheme()
  const tint = hue == null ? undefined : tintHex(hue, scheme)
  useEffect(() => { document.documentElement.style.setProperty('--tint', tint ?? '') }, [tint])  // on the root, so portals (the leader lines) see it too
  const apiRef = useRef(null)    // the globe's control surface, from the latest sigma build
  const nodesBySlug = useMemo(() => Object.fromEntries((graph?.nodes ?? []).map((n) => [n.slug, n])), [graph])
  const relatedTo = (slug) => {  // neighbours on the map, in either direction, deduplicated
    const seen = new Set()
    return (graph?.edges ?? []).flatMap((e) => (e.source === slug ? [e.target] : e.target === slug ? [e.source] : []))
      .filter((s) => nodesBySlug[s] && !seen.has(s) && seen.add(s)).map((s) => nodesBySlug[s])
  }
  const goTo = (slug) => { setNode(nodesBySlug[slug]); apiRef.current?.flyTo(slug, .3, reduced() ? 0 : undefined) }
  const readyRef = useRef(null)  // Result registers its reveal driver here while mounted

  useEffect(() => {
    fetch('/api/graph').then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json() }).then(setGraph).catch(() => setGraphError(true))
  }, [])
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && setNode(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const onAdd = (list) => {
    const { accepted, notice } = acceptFiles(files, [...list])
    setFiles(accepted); setError(notice)
  }
  const onRemove = (i) => setFiles((f) => f.filter((_, k) => k !== i))

  // The server streams one line per photo, then the verdict, then the statement. Photos are paced onto the globe;
  // the verdict follows the last one; the statement fills in whenever the language model is done.
  const onAnalyze = async () => {
    setPhase('analyzing'); setError(''); setNode(null); setProgress([]); setStatement(null)
    const body = new FormData()
    files.forEach((f) => body.append('images', f))
    const hue = hueOfFiles(files)
    const step = pacer(reduced() ? 0 : PACE)
    const photos = []
    let verdict = null
    try {
      const r = await fetch('/api/analyze', { method: 'POST', body })
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText)
      for await (const msg of ndjson(r.body)) {
        if (msg.kind === 'error') throw new Error(msg.detail)
        if (msg.kind === 'photo') {
          photos.push(msg)
          const shown = { ...msg, phrase: phraseFor(msg.matches, msg.names) }  // worded once, so the line doesn't reshuffle on re-render
          step(() => { setProgress((p) => [...p, shown]); apiRef.current?.addPhoto(msg.index, msg, urls.get(files[msg.index]), msg.matches[0].slug) })
        }
        if (msg.kind === 'verdict') {
          verdict = msg
          const h = await hue
          step(() => { setHue(h); setResult({ images: photos, ...msg }); setPhase('result') })
        }
        if (msg.kind === 'statement') step(() => setStatement(msg.statement))
      }
      if (!verdict) throw new Error('The analysis stopped early')
    } catch (e) {
      if (verdict) { setStatement(''); return }  // the result is already on screen; only the statement is missing
      setError(e.message || 'Something went wrong'); setPhase('upload')
    }
  }
  const onReset = () => { setFiles([]); setResult(null); setHue(null); setError(''); setNode(null); setProgress([]); setStatement(null); setPhase('upload') }

  return (
    <main className="stage" data-phase={phase}>
      {/* onReady only reaches the reveal driver for a globe built with a result: after Start over the old Result is still exiting and must not replay onto the idle globe */}
      {graph && <Fade className="graph-fade" duration={.6}>
        <Graph graph={graph} result={phase === 'result' ? result : null} images={images} scheme={scheme} tint={tint} photosVisible={false}
          onSelect={setNode} onReady={(api) => { apiRef.current = api; if (result) readyRef.current?.(api) }} />
      </Fade>}
      <Sheet raise={node?.slug || phase}>
        {graphError && <p className="notice" role="alert">Couldn't load the map</p>}
        <AnimatePresence>{node && <Fade key={node.slug} {...phaseMotion}><NodeDetail node={node} related={relatedTo(node.slug)} onBack={() => setNode(null)} onGo={goTo} /></Fade>}</AnimatePresence>
        <div hidden={!!node} className="phase">{/* hidden, not unmounted: the result keeps driving the reveal behind the detail */}
          {/* The photo list sits between the phase head and foot and stays mounted across upload -> analyzing, so the rows never fade or jump. */}
          <AnimatePresence mode="wait">
            {phase === 'upload' && <Fade key="intro" className="phase" {...phaseMotion}><UploadIntro onAdd={onAdd} error={error} /></Fade>}
          </AnimatePresence>
          <AnimatePresence>
            {phase !== 'result' && <Fade key="photos" exit={{ opacity: 0 }}><PhotoList files={files} urls={urls} progress={phase === 'analyzing' ? progress : null} onRemove={phase === 'upload' ? onRemove : null} /></Fade>}
          </AnimatePresence>
          <AnimatePresence mode="wait">
            {phase === 'upload' && files.length > 0 && <Fade key="go" {...phaseMotion}><AnalyzeButton count={files.length} onAnalyze={onAnalyze} /></Fade>}
            {phase === 'analyzing' && <Fade key="analyzing" className="phase" {...phaseMotion}><Analyzing total={files.length} progress={progress} /></Fade>}
            {phase === 'result' && <Fade key="result" className="phase" {...phaseMotion}><Result files={files} urls={urls} result={result} statement={statement} graph={graph} graphError={graphError} apiRef={apiRef} readyRef={readyRef} onReset={onReset} onGo={goTo} /></Fade>}
          </AnimatePresence>
        </div>
        <Credits />
      </Sheet>
    </main>
  )
}
