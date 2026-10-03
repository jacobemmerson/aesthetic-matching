import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useObjectUrls } from './lib/objectUrls.js'
import { STEP_MS, stepAt } from './lib/loading.js'

export default function Analyzing({ files }) {
  const urls = useObjectUrls(files)
  const [line, setLine] = useState(stepAt(0))
  useEffect(() => {
    const start = Date.now()
    const timer = setInterval(() => setLine(stepAt(Date.now() - start)), STEP_MS)
    return () => clearInterval(timer)
  }, [])
  return (
    <main className="hero">
      <ul className="strip">
        {files.map((f, i) => (
          <motion.li key={`${f.name}:${f.size}`} layoutId={`${f.name}:${f.size}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * .04 }}>
            <img src={urls.get(f)} alt="" /><span className="scan" />
          </motion.li>
        ))}
      </ul>
      <AnimatePresence mode="wait">
        <motion.p key={line} className="display analyzing" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: .3 }}>{line}</motion.p>
      </AnimatePresence>
      <div className="bar" role="progressbar" aria-busy="true"><span /></div>
    </main>
  )
}
