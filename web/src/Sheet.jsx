import { useEffect, useRef, useState } from 'react'
import { animate, motion, useMotionValue } from 'framer-motion'
import { PHONE, useMediaQuery } from './lib/scheme.js'
import { SPRING } from './lib/motion.js'

/** The frosted panel the verdict and node detail live in: a floating card on desktop, a bottom sheet with detents on phones. */
export default function Sheet({ raise, children }) {
  const phone = useMediaQuery(PHONE)
  if (!phone) return <motion.aside className="sheet" initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={SPRING}><div className="sheet-body">{children}</div></motion.aside>
  return <PhoneSheet raise={raise}>{children}</PhoneSheet>
}

const DETENTS = { peek: 150, half: .5, full: .92 }  // px, or a fraction of the viewport height
const px = (d) => (d < 1 ? d * window.innerHeight : d)
const FLING = 10   // frames of the last drag velocity projected ahead when choosing a detent

function PhoneSheet({ raise, children }) {
  // The sheet's height is what animates, not a translation, so the body is exactly the visible part and scrolls within it.
  const height = useMotionValue(0)
  const [detent, setDetent] = useState('half')
  const snapTo = (name) => { setDetent(name); animate(height, px(DETENTS[name]), SPRING) }
  useEffect(() => { snapTo('half') }, [])
  useEffect(() => { if (raise && detent === 'peek') snapTo('half') }, [raise])

  // ponytail: only the handle drags, so the body can always scroll; pulling the sheet down from a scrolled-to-top body is not supported
  const drag = useRef(null)
  const down = (e) => { drag.current = { y0: e.clientY, from: height.get(), v: 0 }; e.currentTarget.setPointerCapture(e.pointerId) }
  const move = (e) => {
    const d = drag.current
    if (!d) return
    const next = Math.min(px(DETENTS.full), Math.max(px(DETENTS.peek), d.from - (e.clientY - d.y0)))
    d.v = next - height.get(); height.set(next)
  }
  const up = () => {
    if (!drag.current) return
    const target = height.get() + drag.current.v * FLING
    drag.current = null
    snapTo(Object.keys(DETENTS).reduce((best, d) => (Math.abs(px(DETENTS[d]) - target) < Math.abs(px(DETENTS[best]) - target) ? d : best)))
  }
  return (
    <motion.aside className="sheet material" style={{ height }}>
      <div className="handle-area" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}><div className="handle" /></div>
      <div className="sheet-body">{children}</div>
    </motion.aside>
  )
}
