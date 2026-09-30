import { motion } from 'framer-motion'
import { useObjectUrls } from './lib/objectUrls.js'

export default function Analyzing({ files }) {
  const urls = useObjectUrls(files)
  return (
    <main className="hero">
      <ul className="strip">
        {files.map((f, i) => (
          <motion.li key={`${f.name}:${f.size}`} layoutId={`${f.name}:${f.size}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * .04 }}>
            <img src={urls.get(f)} alt="" /><span className="scan" />
          </motion.li>
        ))}
      </ul>
      <p className="display analyzing">Reading {files.length} photo{files.length === 1 ? '' : 's'} with CLIP…</p>
      <div className="bar" role="progressbar" aria-busy="true"><span /></div>
    </main>
  )
}
