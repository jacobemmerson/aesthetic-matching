import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

/** Thin lines from each match row to its node on the globe, redrawn every frame so they follow the globe as it turns. */
export default function Leads({ slugs, rows, apiRef }) {
  const svg = useRef(null)
  useEffect(() => {
    let raf
    const draw = () => {
      for (const line of svg.current?.querySelectorAll('line') ?? []) {
        const el = rows.current[line.dataset.slug], at = apiRef.current?.locate(line.dataset.slug)
        const r = el?.getBoundingClientRect(), box = el?.closest('.sheet-body')?.getBoundingClientRect()
        const mid = r && r.top + r.height / 2
        const show = r?.width > 0 && at?.front && box && mid >= box.top && mid <= box.bottom  // only while the row is inside the column's visible scroll area
        line.style.opacity = show ? .45 : 0
        if (show) { line.setAttribute('x1', r.right - 10); line.setAttribute('y1', r.top + r.height / 2); line.setAttribute('x2', at.x); line.setAttribute('y2', at.y) }
      }
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [])
  return createPortal(<svg ref={svg} className="leads" aria-hidden="true">{slugs.map((s) => <line key={s} data-slug={s} />)}</svg>, document.body)
}
