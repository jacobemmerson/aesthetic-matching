import { useState } from 'react'
import { ChevronLeft } from './Icon.jsx'

const sentences = (text) => text.split(/(?<=[.!?])\s+/)
const LEAD = 2  // sentences of the first paragraph shown before "More"

/** A fact from the wiki infobox: two lines, tap to read it all. */
function Fact({ label, text }) {
  const [open, setOpen] = useState(false)
  if (!text) return null
  return (
    <li>
      <button className={'fact' + (open ? ' open' : '')} onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span className="fact-label">{label}</span>
        <span className="fact-text">{text}</span>
      </button>
    </li>
  )
}

/** One aesthetic: the lead, the infobox as rows, and its neighbours on the map as chips. */
export default function NodeDetail({ node, related = [], onBack, onGo }) {
  const [more, setMore] = useState(false)
  const [first = '', ...paragraphs] = (node.description || '').split(/\n+/)  // the scrape keeps the wiki's paragraph breaks
  const parts = sentences(first)
  const lead = parts.slice(0, LEAD).join(' ')
  const rest = [parts.slice(LEAD).join(' '), ...paragraphs].filter(Boolean)
  return (
    <div className="detail">
      <button className="back" onClick={onBack}><ChevronLeft />Back</button>
      <div className="detail-head">
        <h2>{node.name}</h2>
        {node.decade_of_origin && <span className="chip static">{node.decade_of_origin}</span>}
      </div>
      {node.other_names && <p className="aliases">{node.other_names}</p>}
      <div className="desc">
        <p>{lead}{rest.length > 0 && !more && <> <button className="more" onClick={() => setMore(true)}>More</button></>}</p>
        {more && rest.map((t, i) => <p key={i}>{t}{i === rest.length - 1 && <> <button className="more" onClick={() => setMore(false)}>Less</button></>}</p>)}
      </div>
      <ul className="facts">
        <Fact label="Motifs" text={node.key_motifs} />
        <Fact label="Colours" text={node.key_colours} />
        <Fact label="Values" text={node.key_values} />
      </ul>
      {related.length > 0 && (
        <div className="related">
          <span className="fact-label">Related</span>
          <div className="chips">{related.map((n) => <button key={n.slug} className="chip" onClick={() => onGo(n.slug)}>{n.name}</button>)}</div>
        </div>
      )}
      {node.wiki_url && <a className="wiki" href={node.wiki_url} target="_blank" rel="noopener">Read on the Aesthetics Wiki</a>}
    </div>
  )
}
