import { expect, it } from 'vitest'
import { identity, lookAt, multiply, rotateVec, rotationFromDrag, slerpRotation } from './sphere.js'

const unit = (v) => { const n = Math.hypot(...v); return v.map((x) => x / n) }
const close = (a, b) => a.forEach((x, i) => expect(x).toBeCloseTo(b[i], 5))

it('lookAt brings the vector to the front of the sphere', () => {
  for (const v of [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 0, -1], unit([0.3, -0.8, 0.2])]) close(rotateVec(lookAt(v), v), [0, 0, 1])
})

it('rotations stay orthonormal after many drags', () => {
  let R = identity()
  for (let i = 0; i < 300; i++) R = multiply(rotationFromDrag(Math.sin(i) * 9, Math.cos(i * 1.3) * 7, 0.01), R)
  const v = rotateVec(R, [0, 0, 1]), w = rotateVec(R, [1, 0, 0])
  expect(Math.hypot(...v)).toBeCloseTo(1, 6)
  expect(v[0] * w[0] + v[1] * w[1] + v[2] * w[2]).toBeCloseTo(0, 6)
})

it('dragging pulls the front of the sphere along with the pointer', () => {
  expect(rotateVec(rotationFromDrag(10, 0, 0.01), [0, 0, 1])[0]).toBeGreaterThan(0)   // right
  expect(rotateVec(rotationFromDrag(0, 10, 0.01), [0, 0, 1])[1]).toBeLessThan(0)      // down (sigma's y points up)
})

it('slerp hits both endpoints and stays on the sphere midway', () => {
  const A = lookAt([1, 0, 0]), B = lookAt([0, 1, 0])
  close(rotateVec(slerpRotation(A, B, 0), [1, 0, 0]), [0, 0, 1])
  close(rotateVec(slerpRotation(A, B, 1), [0, 1, 0]), [0, 0, 1])
  expect(Math.hypot(...rotateVec(slerpRotation(A, B, 0.5), [0.6, 0.8, 0]))).toBeCloseTo(1, 6)
  close(rotateVec(slerpRotation(A, A, 0.5), [1, 0, 0]), [0, 0, 1])
})
