/** Runs callbacks in order, each at least `gap` ms after the previous one started, so a burst of events reads as a sequence. */
export function pacer(gap) {
  let last = -Infinity
  return (fn) => {
    const at = Math.max(Date.now(), last + gap)
    last = at
    setTimeout(fn, at - Date.now())
  }
}
