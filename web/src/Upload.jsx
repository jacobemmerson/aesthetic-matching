import { useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { MAX_FILES, MIN_FILES } from './lib/files.js'
import Fade from './Fade.jsx'
import { Photos } from './Icon.jsx'
import { SPRING } from './lib/motion.js'

/** Headline and drop target. The photo list itself is rendered by App so it survives the switch to analyzing. */
export function UploadIntro({ onAdd, error }) {
  const [over, setOver] = useState(false)
  const input = useRef(null)
  return (
    <>
      <h1>What's your aesthetic?</h1>
      <p className="sub">Drop a few photos from your life. We'll place them on the map of every internet aesthetic.</p>
      <div className={'drop' + (over ? ' over' : '')} role="button" tabIndex={0}
        onClick={() => input.current.click()} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), input.current.click())}
        onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); onAdd(e.dataTransfer.files) }}>
        <Photos />
        <span>Drop up to {MAX_FILES} photos, or tap to choose</span>
        <small>JPEG or PNG, under 5 MB each.</small>
        <input ref={input} type="file" accept="image/*" multiple hidden onChange={(e) => { onAdd(e.target.files); e.target.value = '' }} />
      </div>
      <AnimatePresence>{error && <Fade as="p" key="error" className="notice" role="alert">{error}</Fade>}</AnimatePresence>
    </>
  )
}

export function AnalyzeButton({ count, onAnalyze }) {
  const missing = MIN_FILES - count
  return (
    <motion.button className="btn" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={SPRING} onClick={onAnalyze} disabled={missing > 0}>
      {missing > 0 ? `Add ${missing} more photo${missing === 1 ? '' : 's'}` : 'Find my aesthetic'}
    </motion.button>
  )
}
