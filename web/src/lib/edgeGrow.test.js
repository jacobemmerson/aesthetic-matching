import { expect, it } from 'vitest'

it('adds a grow attribute and scales the segment by it in the vertex shader', async () => {
  // sigma touches the WebGL globals at import time; node has none
  const gl = { FLOAT: 5126, UNSIGNED_BYTE: 5121, TRIANGLES: 4 }
  globalThis.WebGLRenderingContext ??= gl
  globalThis.WebGL2RenderingContext ??= gl
  const { default: EdgeGrowProgram } = await import('./edgeGrow.js')
  const def = EdgeGrowProgram.prototype.getDefinition.call({})
  expect(def.ATTRIBUTES.at(-1).name).toBe('a_grow')
  expect(def.VERTEX_SHADER_SOURCE).toContain('attribute float a_grow;')
  expect(def.VERTEX_SHADER_SOURCE).toContain('* a_positionCoef * a_grow;')
})
