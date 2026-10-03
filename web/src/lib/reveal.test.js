import { expect, it, vi } from 'vitest'
import { buildRevealSteps, runSteps } from './reveal.js'

const result = { images: [{}, {}, {}], aesthetics: [{ slug: 'a', photos: [0, 2] }, { slug: 'b', photos: [1] }] }

it('builds overview, one step per aesthetic, the overall anchor, a frame, then the headline', () => {
  const steps = buildRevealSteps(result, {})
  expect(steps.map((s) => s.kind)).toEqual(['overview', 'aesthetic', 'aesthetic', 'overall', 'frame', 'headline'])
  expect(steps.filter((s) => s.kind === 'aesthetic').map((s) => s.index)).toEqual([0, 1])
})
it('single aesthetic still yields a full sequence', () => {
  expect(buildRevealSteps({ images: [{}], aesthetics: [{ slug: 'a', photos: [0] }] }, {}).map((s) => s.kind)).toEqual(['overview', 'aesthetic', 'overall', 'frame', 'headline'])
})
it('reduced motion collapses to zero-delay steps in the same order', () => {
  const steps = buildRevealSteps(result, { reducedMotion: true })
  expect(steps.every((s) => s.delay === 0)).toBe(true)
  expect(steps.map((s) => s.kind)).toEqual(['overview', 'aesthetic', 'aesthetic', 'overall', 'frame', 'headline'])
})
it('runSteps calls handlers in order and can be cancelled', async () => {
  vi.useFakeTimers()
  const calls = []
  const cancel = runSteps([{ kind: 'overview', delay: 0 }, { kind: 'photo', index: 0, delay: 100 }, { kind: 'headline', delay: 100 }], { overview: () => calls.push('o'), photo: (i) => calls.push(`p${i}`), headline: () => calls.push('h') })
  await vi.advanceTimersByTimeAsync(150)
  expect(calls).toEqual(['o', 'p0'])
  cancel()
  await vi.advanceTimersByTimeAsync(500)
  expect(calls).toEqual(['o', 'p0'])
  vi.useRealTimers()
})
