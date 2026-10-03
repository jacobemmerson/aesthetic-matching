export const TIMING = { hold: 400, fly: 600, pop: 350, frame: 800 }

export function buildRevealSteps(result, { reducedMotion = false } = {}) {
  const d = (ms) => (reducedMotion ? 0 : ms)
  const steps = [{ kind: 'overview', delay: 0 }]
  result.aesthetics.forEach((_, index) => steps.push({ kind: 'aesthetic', index, delay: d(index === 0 ? TIMING.hold : TIMING.fly + TIMING.pop) }))
  steps.push({ kind: 'overall', delay: d(TIMING.fly + TIMING.pop) })
  steps.push({ kind: 'frame', delay: d(TIMING.fly + TIMING.pop) })
  steps.push({ kind: 'headline', delay: d(TIMING.frame) })
  return steps
}

/** Fires handlers[step.kind](step.index) sequentially, each after its delay. Returns cancel(). */
export function runSteps(steps, handlers) {
  let cancelled = false
  let timer = null
  const go = (i) => {
    if (cancelled || i >= steps.length) return
    timer = setTimeout(() => { if (cancelled) return; handlers[steps[i].kind]?.(steps[i].index); go(i + 1) }, steps[i].delay)
  }
  go(0)
  return () => { cancelled = true; clearTimeout(timer) }
}
