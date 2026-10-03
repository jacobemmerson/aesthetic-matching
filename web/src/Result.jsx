import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Graph from './Graph.jsx'
import DevPanel from './DevPanel.jsx'
import { buildRevealSteps, runSteps, TIMING } from './lib/reveal.js'
import { useObjectUrls } from './lib/objectUrls.js'

const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
const fade = (duration, delay = 0) => (reduced() ? { duration: 0, delay: 0 } : { duration, delay })

export default function Result({ files, result, graph, graphError, onReset }) {
  const [stage, setStage] = useState('reveal')   // 'reveal' | 'done'
  const [dev, setDev] = useState(() => new URLSearchParams(location.search).has('dev'))  // ?dev or the d key
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'd' && !e.metaKey && !e.ctrlKey && e.target.tagName !== 'INPUT') setDev((v) => !v) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  const api = useRef(null)
  const started = useRef(false)
  const shown = useRef({ photos: [], lit: [], overall: false })  // what the reveal has exposed so far, replayed if the graph rebuilds
  const cancel = useRef(() => {})
  const urls = useObjectUrls(files)
  useEffect(() => { if (graphError) setStage('done') }, [graphError])
  // Also resets `started`: StrictMode's simulated unmount cancels the steps, and Graph's effect then re-fires onReady.
  useEffect(() => () => { cancel.current(); started.current = false }, [])

  // Graph rebuilds sigma when its inputs change (e.g. object URLs resolve) and calls onReady each time.
  const onReady = (a) => {
    api.current = a
    shown.current.photos.forEach((i) => a.showPhoto(i))
    shown.current.lit.forEach((slug) => a.light(slug))
    if (shown.current.overall) a.showOverall()
    if (started.current) return
    started.current = true
    const quick = reduced()
    const timers = []
    const later = (fn) => timers.push(setTimeout(fn, quick ? 0 : TIMING.fly))
    const stopSteps = runSteps(buildRevealSteps(result, { reducedMotion: quick }), {
      overview: () => api.current.overview(0),
      aesthetic: (i) => {
        const { slug, photos } = result.aesthetics[i]
        api.current.flyTo(slug, .3, quick ? 0 : TIMING.fly)
        later(() => {
          shown.current.lit.push(slug); api.current.light(slug)
          photos.forEach((k) => { if (!shown.current.photos.includes(k)) { shown.current.photos.push(k); api.current.showPhoto(k) } })
        })
      },
      overall: () => {
        api.current.flyTo('overall', .3, quick ? 0 : TIMING.fly)
        later(() => { shown.current.overall = true; api.current.showOverall() })
      },
      frame: () => api.current.overview(quick ? 0 : TIMING.frame),
      headline: () => { setStage('done'); shown.current.photos = []; api.current.hidePhotos() },  // photos come back while You is hovered
    })
    cancel.current = () => { stopSteps(); timers.forEach(clearTimeout) }
  }

  const fly = (id) => api.current?.flyTo(id, .3, reduced() ? 0 : undefined)
  return (
    <main className="result">
      {graph && <Graph graph={graph} result={result} files={files} onReady={onReady} photosVisible={false} />}
      <header className="result-head">
        {!graph && !graphError && <p className="sub">Loading the map…</p>}
        {graphError && <p className="notice">Couldn't load the map</p>}
        <AnimatePresence>{stage === 'done' && (
          <motion.div key="verdict" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={fade(.5)}>
            <ol className="verdict">
              {result.aesthetics.map((a, i) => (
                <motion.li key={a.slug} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={fade(.4, .15 * i)}>
                  <button className="aes" onClick={() => { fly(a.slug); api.current?.select(a.slug) }}>
                    <span className="thumbs">{a.photos.map((k) => files[k] && urls.get(files[k]) && <img key={k} src={urls.get(files[k])} alt="" />)}</span>
                    <em>{result.names[a.slug]}</em>
                  </button>
                </motion.li>
              ))}
            </ol>
            <motion.div className="score" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={fade(.4, .15 * result.aesthetics.length + .2)}>
              <div className="score-head"><span>Score</span><strong>{result.basic_score}<small> / 100</small></strong></div>
              <div className="meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={result.basic_score}><span style={{ width: `${result.basic_score}%` }} /></div>
              <div className="meter-ends"><small>Niche</small><small>Basic</small></div>
              <p className="statement">{result.statement}</p>
            </motion.div>
            <div className="actions">
              <button className="btn ghost" onClick={onReset}>Start over</button>
            </div>
          </motion.div>
        )}</AnimatePresence>
      </header>
      {dev && <DevPanel result={result} files={files} onClose={() => setDev(false)} />}
    </main>
  )
}
