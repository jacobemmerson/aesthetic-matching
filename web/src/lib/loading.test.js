import { expect, it } from 'vitest'
import { STEPS, stepAt } from './loading.js'

it('walks the steps on a fixed cadence and holds the last one', () => {
  expect(stepAt(0)).toBe(STEPS[0])
  expect(stepAt(STEPS.length * 3000 + 60000)).toBe(STEPS.at(-1))
  const seen = new Set(Array.from({ length: 40 }, (_, i) => stepAt(i * 1000)))
  expect([...seen]).toEqual(STEPS)  // every step shows, in order, with none skipped
})
