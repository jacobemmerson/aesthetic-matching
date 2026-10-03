import Fade from './Fade.jsx'

/** Developer view: every photo's match distribution (probability and raw score), plus the aggregate. */
export default function DevPanel({ result, files, urls, onClose }) {
  const rows = [...result.images.map((img, k) => ({ key: k, label: `photo ${k + 1}`, src: urls.get(files[k]), matches: img.matches })),
                { key: 'overall', label: 'You (mixture of the photos)', matches: result.overall.matches.slice(0, 5) }]
  return (
    <Fade as="aside" className="dev">
      <button className="close" aria-label="close" onClick={onClose}>×</button>
      <h3>Match distributions</h3>
      {rows.map((r) => (
        <section key={r.key}>
          <header>{r.src ? <img src={r.src} alt="" /> : <span className="dot" />}<span>{r.label}</span></header>
          <ol>
            {r.matches.map((m) => (
              <li key={m.slug}>
                <span className="name">{result.names[m.slug] || m.slug}</span>
                <span className="bar"><i style={{ width: `${Math.max(1, m.prob * 100)}%` }} /></span>
                <code>{(m.prob * 100).toFixed(1)}%{m.score !== undefined && ` · ${m.score.toFixed(3)}`}</code>
              </li>
            ))}
          </ol>
        </section>
      ))}
      <p className="hint">score {result.basic_score} / 100 · probabilities are a softmax over all nodes; only the top 5 are listed</p>
    </Fade>
  )
}
