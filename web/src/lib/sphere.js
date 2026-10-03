// 3x3 rotation matrices as nested arrays; vectors as [x, y, z]. Enough for spinning a point cloud.
export const identity = () => [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

export const multiply = (A, B) => A.map((row) => [0, 1, 2].map((j) => row[0] * B[0][j] + row[1] * B[1][j] + row[2] * B[2][j]))

export const rotateVec = (R, v) => R.map((row) => row[0] * v[0] + row[1] * v[1] + row[2] * v[2])

const transpose = (A) => [0, 1, 2].map((j) => [A[0][j], A[1][j], A[2][j]])

/** Rodrigues' formula: rotation of `angle` radians about a unit `axis`. */
export function axisAngle([x, y, z], angle) {
  const c = Math.cos(angle), s = Math.sin(angle), t = 1 - c
  return [
    [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
    [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
    [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
  ]
}

/** Screen drag of (dx, dy) pixels spins the sphere about the vertical then the horizontal axis. */
export const rotationFromDrag = (dx, dy, speed) => multiply(axisAngle([1, 0, 0], -dy * speed), axisAngle([0, 1, 0], dx * speed))

/** Rotation that brings unit vector v to the front, (0, 0, 1). */
export function lookAt([x, y, z]) {
  const d = Math.max(-1, Math.min(1, z))
  if (d > 1 - 1e-9) return identity()
  if (d < -1 + 1e-9) return axisAngle([1, 0, 0], Math.PI)
  const axis = [y, -x, 0], n = Math.hypot(axis[0], axis[1])
  return axisAngle([axis[0] / n, axis[1] / n, 0], Math.acos(d))
}

/** Interpolate rotations A -> B along the shortest arc: apply a fraction t of the rotation B·Aᵀ. */
export function slerpRotation(A, B, t) {
  const D = multiply(B, transpose(A))
  const c = Math.max(-1, Math.min(1, (D[0][0] + D[1][1] + D[2][2] - 1) / 2))
  const angle = Math.acos(c)
  if (angle < 1e-9) return A
  let axis
  if (Math.PI - angle < 1e-6) {  // 180 degrees: the skew part vanishes, take the axis from the diagonal
    const k = [0, 1, 2].reduce((best, i) => (D[i][i] > D[best][best] ? i : best), 0)
    axis = [0, 1, 2].map((i) => (i === k ? Math.sqrt(Math.max(0, (D[k][k] + 1) / 2)) : D[k][i] / (2 * Math.sqrt(Math.max(1e-12, (D[k][k] + 1) / 2)))))
  } else {
    const s = 2 * Math.sin(angle)
    axis = [(D[2][1] - D[1][2]) / s, (D[0][2] - D[2][0]) / s, (D[1][0] - D[0][1]) / s]
  }
  return multiply(axisAngle(axis, angle * t), A)
}
