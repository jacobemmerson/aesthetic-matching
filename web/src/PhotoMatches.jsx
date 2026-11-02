import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronRight } from './Icon.jsx'
import { reduced } from './lib/motion.js'

const pct = (p) => `${Math.round(p * 100)}%`

/** Why this match: each photo's top aesthetics with the model's probabilities. Opening a photo shows it on the globe. */
export default function PhotoMatches({ files, urls, result, apiRef, onGo }) {
  const [open, setOpen] = useState(null)
  const toggle = (k) => {
    const next = open === k ? null : k
    setOpen(next)
    if (next === null) apiRef.current?.hidePhotos()
    else { apiRef.current?.showPhoto(k); apiRef.current?.flyTo(`photo-${k}`, .35, reduced() ? 0 : undefined) }
  }
  return (
    <section className="why">
      <span className="fact-label">Why these matches</span>
      <ul className="photos">
        {result.images.map((img, k) => files[k] && (
          <li key={k} className={open === k ? 'open' : ''}>
            <button className="row" onClick={() => toggle(k)} aria-expanded={open === k}>
              <span className="thumb"><img src={urls.get(files[k])} alt="" /></span>
              <span className="photo-text"><span className="match">{result.names[img.matches[0].slug]}</span><span className="muted">{pct(img.matches[0].prob)} match</span></span>
              <ChevronRight />
            </button>
            <AnimatePresence initial={false}>
              {open === k && (
                <motion.ol className="breakdown" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: .25 }}>
                  {img.matches.slice(0, 3).map((m) => (
                    <li key={m.slug}>
                      <button className="alt" onClick={() => onGo(m.slug)}>
                        <span>{result.names[m.slug] || m.slug}</span>
                        <span className="mini"><i style={{ width: pct(m.prob) }} /></span>
                        <code>{pct(m.prob)}</code>
                      </button>
                    </li>
                  ))}
                </motion.ol>
              )}
            </AnimatePresence>
          </li>
        ))}
      </ul>
    </section>
  )
}
