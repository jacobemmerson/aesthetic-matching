import { expect, it, vi } from 'vitest'
import { buildRevealSteps, runSteps } from './reveal.js'

const result = { images: [{}, {}, {}] }

it('builds overview, one photo step per image, a frame, then the headline', () => {
  const kinds = buildRevealSteps(result, {}).map((s) => s.kind)
  expect(kinds).toEqual(['overview', 'photo', 'photo', 'photo', 'frame', 'headline'])
  expect(buildRevealSteps(result, {}).filter((s) => s.kind === 'photo').map((s) => s.index)).toEqual([0, 1, 2])
})
it('single photo still yields a full sequence', () => {
  expect(buildRevealSteps({ images: [{}] }, {}).map((s) => s.kind)).toEqual(['overview', 'photo', 'frame', 'headline'])
})
it('reduced motion collapses to zero-delay steps in the same order', () => {
  const steps = buildRevealSteps(result, { reducedMotion: true })
  expect(steps.every((s) => s.delay === 0)).toBe(true)
  expect(steps.map((s) => s.kind)).toEqual(['overview', 'photo', 'photo', 'photo', 'frame', 'headline'])
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
