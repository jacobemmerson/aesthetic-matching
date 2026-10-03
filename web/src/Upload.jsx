import { useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { MAX_FILES, MIN_FILES } from './lib/files.js'
import Fade from './Fade.jsx'

const fan = (i, n) => ({ rotate: (i - (n - 1) / 2) * 6, y: Math.abs(i - (n - 1) / 2) * 6 })

export default function Upload({ files, urls, onAdd, onRemove, onAnalyze, error }) {
  const [over, setOver] = useState(false)
  const input = useRef(null)
  const missing = MIN_FILES - files.length
  return (
    <main className="hero">
      <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .6 }}>What's your aesthetic?</motion.h1>
      <p className="sub">Drop a few photos from your life. We'll place them on the map of every internet aesthetic.</p>

      <div className={'drop' + (over ? ' over' : '')} role="button" tabIndex={0}
        onClick={() => input.current.click()} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), input.current.click())}
        onDragOver={(e) => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); onAdd(e.dataTransfer.files) }}>
        <span>Drop up to {MAX_FILES} photos here, or click to choose</span>
        <small>JPEG or PNG, under 5 MB each. Nothing is stored.</small>
        <input ref={input} type="file" accept="image/*" multiple hidden onChange={(e) => { onAdd(e.target.files); e.target.value = '' }} />
      </div>

      <AnimatePresence>{error && <Fade as="p" key="error" className="notice" role="alert">{error}</Fade>}</AnimatePresence>

      <motion.ul className="stack" layout>
        <AnimatePresence>
          {files.map((f, i) => (
            <motion.li key={`${f.name}:${f.size}`} layout
              initial={{ opacity: 0, scale: .6, ...fan(i, files.length) }}
              animate={{ opacity: 1, scale: 1, rotate: 0, y: 0 }}
              exit={{ opacity: 0, scale: .6 }}
              transition={{ type: 'spring', stiffness: 260, damping: 22, delay: i * .05 }}>
              <img src={urls.get(f)} alt="" />
              <button className="remove" aria-label={`remove ${f.name}`} onClick={() => onRemove(i)}>×</button>
            </motion.li>
          ))}
        </AnimatePresence>
      </motion.ul>

      <AnimatePresence>
        {files.length > 0 && (
          <motion.button className="btn" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} onClick={onAnalyze} disabled={missing > 0}>
            {missing > 0 ? `Add ${missing} more photo${missing === 1 ? '' : 's'}` : 'Find my aesthetic'}
          </motion.button>
        )}
      </AnimatePresence>
    </main>
  )
}
