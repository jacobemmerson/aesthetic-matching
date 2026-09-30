export default function Upload({ files, onAdd, onRemove, onAnalyze, error }) {
  return (
    <main>
      <h1>What's your aesthetic?</h1>
      <input type="file" accept="image/*" multiple onChange={(e) => onAdd(e.target.files)} />
      <ul>{files.map((f, i) => <li key={i}>{f.name} <button onClick={() => onRemove(i)}>remove</button></li>)}</ul>
      {error && <p role="alert">{error}</p>}
      {files.length > 0 && <button className="btn" onClick={onAnalyze}>Find my aesthetic</button>}
    </main>
  )
}
