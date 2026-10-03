import { expect, it, vi } from 'vitest'
import { mixHex, tween } from './tween.js'

it('mixes two hex colours by t', () => {
  expect(mixHex('#000000', '#ffffff', 0)).toBe('#000000')
  expect(mixHex('#000000', '#ffffff', 1)).toBe('#ffffff')
  expect(mixHex('#000000', '#ff4d6d', 0.5)).toBe('#802737')
})

it('tween calls onFrame with eased progress until 1, and can be cancelled', () => {
  vi.useFakeTimers()
  const frames = []
  tween(100, (t) => frames.push(t))
  vi.advanceTimersByTime(50)
  expect(frames.length).toBeGreaterThan(0)
  expect(frames.at(-1)).toBeGreaterThan(0)
  expect(frames.at(-1)).toBeLessThan(1)
  vi.advanceTimersByTime(100)
  expect(frames.at(-1)).toBe(1)
  const count = frames.length
  vi.advanceTimersByTime(100)
  expect(frames.length).toBe(count)
  const more = []
  const stop = tween(100, (t) => more.push(t)); stop()
  vi.advanceTimersByTime(200)
  expect(more).toEqual([])
  vi.useRealTimers()
})

it('tween with zero duration jumps straight to 1', () => {
  const frames = []
  tween(0, (t) => frames.push(t))
  expect(frames).toEqual([1])
})
