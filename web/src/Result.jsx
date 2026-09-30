import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Graph from './Graph.jsx'
import { buildRevealSteps, runSteps, TIMING } from './lib/reveal.js'
import { shareOrDownload } from './lib/shareCard.js'
import { useObjectUrls } from './lib/objectUrls.js'

const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

export default function Result({ files, result, onReset }) {
  const [graph, setGraph] = useState(null)
  const [stage, setStage] = useState('reveal')   // 'reveal' | 'done'
  const api = useRef(null)
  const started = useRef(false)
  const shown = useRef([])                       // photo indexes revealed so far
  const cancel = useRef(() => {})
  const urls = useObjectUrls(files)
  useEffect(() => { fetch('/api/graph').then((r) => r.json()).then(setGraph) }, [])
  useEffect(() => () => cancel.current(), [])

  // Graph rebuilds sigma when its inputs change (e.g. object URLs resolve) and calls onReady each time.
  const onReady = (a) => {
    api.current = a
    shown.current.forEach((i) => a.showPhoto(i))
    if (started.current) return
    started.current = true
    const quick = reduced()
    const timers = []
    const stopSteps = runSteps(buildRevealSteps(result, { reducedMotion: quick }), {
      overview: () => api.current.overview(0),
      photo: (i) => {
        api.current.flyTo(`photo-${i}`, .3, quick ? 0 : TIMING.fly)
        timers.push(setTimeout(() => { shown.current.push(i); api.current.showPhoto(i) }, quick ? 0 : TIMING.fly))
      },
      frame: () => api.current.overview(quick ? 0 : TIMING.frame),
      headline: () => setStage('done'),
    })
    cancel.current = () => { stopSteps(); timers.forEach(clearTimeout) }
  }

  const names = result.overall.map((m) => result.names[m.slug])
  return (
    <main className="result">
      <header className="result-head">
        <div>
          <AnimatePresence>{stage === 'done' && (
            <motion.h1 initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5 }}>
              You are {names.map((n, i) => <span key={n}>{i > 0 && ' · '}<em>{n}</em></span>)}
            </motion.h1>
          )}</AnimatePresence>
          {stage === 'done' && (
            <motion.div className="chips" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .3 }}>
              {result.images.map((img, k) => files[k] && (
                <button key={k} className="chip" onClick={() => api.current?.flyTo(`photo-${k}`, .3)}>
                  {urls.get(files[k]) && <img src={urls.get(files[k])} alt="" />} {result.names[img.matches[0].slug]}
                </button>
              ))}
            </motion.div>
          )}
        </div>
        {stage === 'done' && (
          <motion.div className="actions" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: .6 }}>
            <button className="btn" onClick={() => shareOrDownload(result, graph, files)}>Download card</button>
            <button className="btn ghost" onClick={onReset}>Start over</button>
          </motion.div>
        )}
      </header>
      {graph && <Graph graph={graph} result={result} files={files} onReady={onReady} photosVisible={false} />}
    </main>
  )
}
