import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { pacer } from './pace.js'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

it('spaces a burst out by the gap and runs an isolated call at once', () => {
  const seen = []
  const step = pacer(500)
  step(() => seen.push('a')); step(() => seen.push('b')); step(() => seen.push('c'))
  vi.advanceTimersByTime(0); expect(seen).toEqual(['a'])
  vi.advanceTimersByTime(499); expect(seen).toEqual(['a'])
  vi.advanceTimersByTime(1); expect(seen).toEqual(['a', 'b'])
  vi.advanceTimersByTime(500); expect(seen).toEqual(['a', 'b', 'c'])
  vi.advanceTimersByTime(2000); step(() => seen.push('d')); vi.advanceTimersByTime(0)
  expect(seen).toEqual(['a', 'b', 'c', 'd'])
})

it('a zero gap runs everything immediately in order', () => {
  const seen = [], step = pacer(0)
  step(() => seen.push(1)); step(() => seen.push(2)); vi.advanceTimersByTime(0)
  expect(seen).toEqual([1, 2])
})
