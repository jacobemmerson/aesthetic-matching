import { AnimatePresence, motion } from 'framer-motion'
import { lineFor } from './lib/loading.js'
import { SPRING } from './lib/motion.js'

/** The status line and progress bar under the photo list while the server works through the photos. */
export default function Analyzing({ total, progress }) {
  const line = lineFor({ shown: progress, total })
  const pct = total ? (progress.length / total) * 100 : 0
  return (
    <>
      <AnimatePresence mode="wait">
        <motion.p key={line} className="analyzing" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: .18 }}>{line}</motion.p>
      </AnimatePresence>
      <div className={'bar' + (pct ? '' : ' busy')} role="progressbar" aria-valuemin={0} aria-valuemax={total} aria-valuenow={progress.length}>
        <motion.span animate={{ width: `${Math.max(pct, 6)}%` }} transition={SPRING} />
      </div>
    </>
  )
}
