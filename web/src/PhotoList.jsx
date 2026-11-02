import { AnimatePresence, motion } from 'framer-motion'
import Fade from './Fade.jsx'
import { X } from './Icon.jsx'
import { SPRING } from './lib/motion.js'

/** The uploaded photos as a column of rows. The same rows stay mounted from upload through analysis:
 *  while uploading each has a remove button; while analyzing each gets its best match as it arrives. */
export default function PhotoList({ files, urls, progress, onRemove }) {
  const analyzing = progress != null
  const done = new Map((progress ?? []).map((p) => [p.index, p]))
  return (
    <motion.ul className="photos" layout>
      <AnimatePresence initial={false}>
        {files.map((f, i) => {
          const hit = done.get(i)
          return (
            <motion.li key={`${f.name}:${f.size}`} layout initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, scale: .96 }} transition={SPRING}>
              <span className="thumb"><img src={urls.get(f)} alt="" />{analyzing && !hit && <span className="scan" />}</span>
              <span className="photo-text">
                <AnimatePresence mode="wait" initial={false}>
                  {hit
                    ? <Fade as="span" key="hit" className="match">{hit.name}</Fade>
                    : <Fade as="span" key="name" className="muted filename">{analyzing ? 'Reading…' : f.name}</Fade>}
                </AnimatePresence>
              </span>
              {onRemove && <button className="icon-btn" aria-label={`remove ${f.name}`} onClick={() => onRemove(i)}><X /></button>}
            </motion.li>
          )
        })}
      </AnimatePresence>
    </motion.ul>
  )
}
