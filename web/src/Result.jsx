export default function Result({ files, result, onReset }) {
  const names = result.overall.map((m) => result.names[m.slug]).join(' · ')
  return <main><h1>You are {names}</h1><button className="btn ghost" onClick={onReset}>Start over</button></main>
}
