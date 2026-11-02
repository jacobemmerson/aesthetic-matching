import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import DevPanel from './DevPanel.jsx'
import Leads from './Leads.jsx'
import PhotoMatches from './PhotoMatches.jsx'
import { ChevronRight } from './Icon.jsx'
import Fade from './Fade.jsx'
import { buildRevealSteps, runSteps, TIMING } from './lib/reveal.js'
import { reduced } from './lib/motion.js'
const fade = (duration, delay = 0) => (reduced() ? { duration: 0, delay: 0 } : { duration, delay })

/** The verdict, and the reveal choreography that precedes it. Mounted inside the sheet while the globe lives in App. */
export default function Result({ files, urls, result, statement, graph, graphError, apiRef, readyRef, onReset, onGo }) {
  const [stage, setStage] = useState('reveal')   // 'reveal' | 'done'
  const [dev, setDev] = useState(() => new URLSearchParams(location.search).has('dev'))  // ?dev or the d key
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'd' && !e.metaKey && !e.ctrlKey && e.target.tagName !== 'INPUT') setDev((v) => !v) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  const started = useRef(false)
  const rows = useRef({})  // slug -> row element, for the leader lines
  const shown = useRef({ photos: [], lit: [], overall: false })  // what the reveal has exposed so far, replayed if the graph rebuilds
  const cancel = useRef(() => {})
  useEffect(() => { if (graphError) setStage('done') }, [graphError])

  // The globe calls this again whenever it rebuilds sigma (StrictMode's double mount, a theme change), so replay what the reveal has shown.
  const onReady = (api) => {
    shown.current.photos.forEach((i) => api.showPhoto(i))
    shown.current.lit.forEach((slug) => api.light(slug))
    if (shown.current.overall) api.showOverall()
    if (started.current) return
    started.current = true
    const quick = reduced()
    const timers = []
    const later = (fn) => timers.push(setTimeout(fn, quick ? 0 : TIMING.fly))
    const a = () => apiRef.current
    const stopSteps = runSteps(buildRevealSteps(result, { reducedMotion: quick }), {
      overview: () => a().overview(0),
      aesthetic: (i) => {
        const { slug, photos } = result.aesthetics[i]
        a().flyTo(slug, .3, quick ? 0 : TIMING.fly)
        later(() => {
          shown.current.lit.push(slug); a().light(slug)
          photos.forEach((k) => { if (!shown.current.photos.includes(k)) { shown.current.photos.push(k); a().showPhoto(k) } })
        })
      },
      overall: () => {
        a().flyTo('overall', .3, quick ? 0 : TIMING.fly)
        later(() => { shown.current.overall = true; a().showOverall() })
      },
      frame: () => a().overview(quick ? 0 : TIMING.frame),
      headline: () => { setStage('done'); shown.current.photos = []; a().hidePhotos() },  // photos come back while You is hovered
    })
    cancel.current = () => { stopSteps(); timers.forEach(clearTimeout) }
  }
  // The globe may already be built (it was there during upload) or may rebuild after this mounts; either way the driver runs once.
  // The cleanup also resets `started`: StrictMode's simulated unmount cancels the steps, and the next onReady starts over.
  useEffect(() => {
    readyRef.current = onReady
    if (apiRef.current) onReady(apiRef.current)
    return () => { readyRef.current = null; cancel.current(); started.current = false }
  }, [])

  const fly = (id) => apiRef.current?.flyTo(id, .3, reduced() ? 0 : undefined)
  return (
    <>
      {!graph && !graphError && <p className="muted">Loading the map…</p>}
      {graph && stage === 'reveal' && <p className="muted">Placing your photos…</p>}
      <AnimatePresence>{stage === 'done' && (
        <motion.div key="verdict" className="verdict" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={fade(.5)}>
          <ol className="list">
            {result.aesthetics.map((a, i) => (
              <motion.li key={a.slug} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={fade(.4, .15 * i)}>
                <button className="row" ref={(el) => { rows.current[a.slug] = el }} onClick={() => { fly(a.slug); apiRef.current?.select(a.slug) }}>
                  <span className="thumbs">{a.photos.map((k) => files[k] && urls.get(files[k]) && <img key={k} src={urls.get(files[k])} alt="" />)}</span>
                  <span className="name">{result.names[a.slug]}</span>
                  <ChevronRight />
                </button>
              </motion.li>
            ))}
          </ol>
          <motion.div className="score" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={fade(.4, .15 * result.aesthetics.length + .2)}>
            <div className="score-head"><span>Score</span><strong>{result.basic_score}<small> / 100</small></strong></div>
            <div className="meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={result.basic_score}><motion.span initial={{ width: 0 }} animate={{ width: `${result.basic_score}%` }} transition={fade(.8, .2)} /></div>
            <div className="meter-ends"><small>Niche</small><small>Basic</small></div>
          </motion.div>
          <AnimatePresence mode="wait">
            {statement == null
              ? <Fade as="p" key="writing" className="statement muted">Writing your verdict…</Fade>
              : <Fade as="p" key="statement" className="statement" duration={.5}>{statement}</Fade>}
          </AnimatePresence>
          <PhotoMatches files={files} urls={urls} result={result} apiRef={apiRef} onGo={onGo} />
          <button className="btn secondary" onClick={onReset}>Start over</button>
          <Leads slugs={result.aesthetics.map((a) => a.slug)} rows={rows} apiRef={apiRef} />
        </motion.div>
      )}</AnimatePresence>
      <AnimatePresence>{dev && <DevPanel key="dev" result={result} files={files} urls={urls} onClose={() => setDev(false)} />}</AnimatePresence>
    </>
  )
}
