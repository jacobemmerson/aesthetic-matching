import { expect, it } from 'vitest'
import { syncObjectUrls } from './objectUrls.js'

it('creates only for new files and revokes removed ones', () => {
  const [a, b, c] = [{}, {}, {}]
  const created = [], revoked = []
  const api = { create: (f) => { created.push(f); return `url${created.length}` }, revoke: (u) => revoked.push(u) }
  const first = syncObjectUrls(new Map(), [a, b], api)
  const second = syncObjectUrls(first, [b, c], api)
  expect(created).toEqual([a, b, c])
  expect(revoked).toEqual([first.get(a)])
  expect(second.get(b)).toBe(first.get(b))
})
