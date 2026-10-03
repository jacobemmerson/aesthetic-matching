const hex = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16))

export function mixHex(from, to, t) {
  const [a, b] = [hex(from), hex(to)]
  return '#' + a.map((v, i) => Math.round(v + (b[i] - v) * t).toString(16).padStart(2, '0')).join('')
}

const raf = (fn) => (typeof requestAnimationFrame === 'function' ? requestAnimationFrame(fn) : setTimeout(fn, 16))

/** Calls onFrame(t) with ease-out t in (0, 1] until done; returns cancel(). Zero duration fires onFrame(1) at once. */
export function tween(duration, onFrame) {
  if (duration <= 0) { onFrame(1); return () => {} }
  let cancelled = false
  const start = performance.now()
  const step = () => {
    if (cancelled) return
    const t = Math.min(1, (performance.now() - start) / duration)
    onFrame(1 - (1 - t) ** 3)
    if (t < 1) raf(step)
  }
  raf(step)
  return () => { cancelled = true }
}
