import { expect, it } from 'vitest'
import { searchNodes } from './search.js'

const nodes = [{ slug: 'goth', name: 'Goth' }, { slug: 'pastel-goth', name: 'Pastel Goth' }, { slug: 'gothic', name: 'Gothic' }, { slug: 'cottagecore', name: 'Cottagecore' }]

it('prefix matches rank before substring matches, case-insensitive', () => {
  expect(searchNodes(nodes, 'got').map((n) => n.slug)).toEqual(['goth', 'gothic', 'pastel-goth'])
})
it('empty query returns nothing and limit caps results', () => {
  expect(searchNodes(nodes, '')).toEqual([])
  expect(searchNodes(nodes, 'o', 2)).toHaveLength(2)
})
