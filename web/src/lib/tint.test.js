import { expect, it } from 'vitest'
import { dominantHue, tintHex } from './tint.js'

const pixels = (rgb, n = 16) => Uint8ClampedArray.from(Array.from({ length: n }, () => [...rgb, 255]).flat())

it('finds the hue of a saturated colour in oklch degrees', () => {
  const red = dominantHue(pixels([255, 0, 0]))
  expect(red).toBeGreaterThan(20); expect(red).toBeLessThan(40)       // oklch red ≈ 29°
  const blue = dominantHue(pixels([0, 0, 255]))
  expect(blue).toBeGreaterThan(255); expect(blue).toBeLessThan(275)   // oklch blue ≈ 264°
})

it('ignores grey, so grey photos yield no hue', () => {
  expect(dominantHue(pixels([128, 128, 128]))).toBeNull()
  expect(dominantHue(new Uint8ClampedArray(0))).toBeNull()
})

it('weights by chroma, so a few vivid pixels beat many dull ones', () => {
  const mixed = Uint8ClampedArray.from([...pixels([130, 128, 128], 60), ...pixels([0, 0, 255], 4)])
  const h = dominantHue(mixed)
  expect(h).toBeGreaterThan(255); expect(h).toBeLessThan(275)
})

it('makes an in-gamut hex tint that differs per scheme and keeps the hue', () => {
  for (const h of [29, 142, 264, 100]) {
    const light = tintHex(h, 'light'), dark = tintHex(h, 'dark')
    expect(light).toMatch(/^#[0-9a-f]{6}$/); expect(dark).toMatch(/^#[0-9a-f]{6}$/)
    expect(light).not.toBe(dark)
    expect(Math.abs(dominantHue(hex(light)) - h)).toBeLessThan(6)
  }
})

const hex = (c) => Uint8ClampedArray.from([...[1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)), 255])
