import { describe, expect, it } from 'vitest'
import { acceptFiles, MAX_BYTES, MAX_FILES, MIN_FILES } from './files.js'

const img = (name, size = 1000, type = 'image/jpeg') => ({ name, size, type })

describe('acceptFiles', () => {
  it('keeps valid images and appends to existing', () => {
    const { accepted, notice } = acceptFiles([img('a.jpg')], [img('b.png', 10, 'image/png')])
    expect(accepted.map((f) => f.name)).toEqual(['a.jpg', 'b.png'])
    expect(notice).toBe('')
  })
  it('drops non-images and oversized files with a notice naming why', () => {
    const { accepted, notice } = acceptFiles([], [img('doc.pdf', 10, 'application/pdf'), img('big.jpg', MAX_BYTES + 1), img('ok.jpg')])
    expect(accepted.map((f) => f.name)).toEqual(['ok.jpg'])
    expect(notice).toMatch(/doc\.pdf.*not an image/i)
    expect(notice).toMatch(/big\.jpg.*5 MB/i)
  })
  it('caps at MAX_FILES and says how many were left out', () => {
    const many = Array.from({ length: 12 }, (_, i) => img(`p${i}.jpg`))
    const { accepted, notice } = acceptFiles([], many)
    expect(accepted).toHaveLength(MAX_FILES)
    expect(notice).toMatch(/2 more/)
  })
  it('needs at least three photos for an analysis', () => {
    expect(MIN_FILES).toBe(3)
  })
  it('ignores exact duplicates (same name and size)', () => {
    const { accepted } = acceptFiles([img('a.jpg')], [img('a.jpg')])
    expect(accepted).toHaveLength(1)
  })
})
