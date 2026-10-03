import { EdgeRectangleProgram } from 'sigma/rendering'

const FULL = 'vec2 position = a_positionStart * (1.0 - a_positionCoef) + a_positionEnd * a_positionCoef;'
const PARTIAL = 'vec2 position = a_positionStart + (a_positionEnd - a_positionStart) * a_positionCoef * a_grow;'

/** Sigma's rectangle edge, plus a per-edge `grow` (0-1) that draws only that fraction of the
 * segment from the `growFrom` end ('source' | 'target'). Lets a highlight travel along an edge. */
export default class EdgeGrowProgram extends EdgeRectangleProgram {
  getDefinition() {
    const def = super.getDefinition()
    if (!def.VERTEX_SHADER_SOURCE.includes(FULL)) throw new Error('sigma edge shader changed; update edgeGrow.js')
    return {
      ...def,
      VERTEX_SHADER_SOURCE: def.VERTEX_SHADER_SOURCE.replace('attribute vec4 a_id;', 'attribute vec4 a_id;\nattribute float a_grow;').replace(FULL, PARTIAL),
      ATTRIBUTES: [...def.ATTRIBUTES, { name: 'a_grow', size: 1, type: WebGLRenderingContext.FLOAT }],
    }
  }

  processVisibleItem(edgeIndex, startIndex, sourceData, targetData, data) {
    const flip = data.growFrom === 'target'
    super.processVisibleItem(edgeIndex, startIndex, flip ? targetData : sourceData, flip ? sourceData : targetData, data)
    this.array[startIndex + 8] = data.grow ?? 1  // after the 8 floats the parent writes per edge
  }
}
