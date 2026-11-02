import { expect, it } from 'vitest'
import { lineFor, phraseFor } from './loading.js'

const names = { goth: 'Goth', emo: 'Emo', y2k: 'Y2K' }
const first = () => 0  // always the first template, so the wording is predictable

it('words the top match by its strength', () => {
  expect(phraseFor([{ slug: 'goth', prob: .9 }, { slug: 'emo', prob: .02 }], names, first)).toBe('Definitely Goth…')
  expect(phraseFor([{ slug: 'goth', prob: .5 }, { slug: 'emo', prob: .02 }], names, first)).toBe('Feeling Goth…')
  expect(phraseFor([{ slug: 'goth', prob: .2 }, { slug: 'emo', prob: .02 }], names, first)).toBe('Picking up a Goth vibe…')
})

it('mentions a runner-up when it is more than noise, worded by its own strength', () => {
  expect(phraseFor([{ slug: 'goth', prob: .55 }, { slug: 'emo', prob: .35 }], names, first)).toBe('Feeling Goth, and some Emo…')
  expect(phraseFor([{ slug: 'goth', prob: .8 }, { slug: 'y2k', prob: .1 }], names, first)).toBe('Definitely Goth, with a hint of Y2K…')
  expect(phraseFor([{ slug: 'goth', prob: .8 }, { slug: 'y2k', prob: .07 }], names, first)).toBe('Definitely Goth…')
})

it('samples a different template with a different draw and falls back to the slug without a name', () => {
  expect(phraseFor([{ slug: 'goth', prob: .9 }], names, () => .99)).toBe('That is Goth…')
  expect(phraseFor([{ slug: 'nightcore', prob: .9 }], {}, first)).toBe('Definitely nightcore…')
})

it('narrates the stream: waiting, latest photo, all in, verdict', () => {
  expect(lineFor({ shown: [], total: 3 })).toMatch(/Reading/)
  expect(lineFor({ shown: [{ index: 0, name: 'Goth', phrase: 'Definitely Goth…' }], total: 3 })).toBe('Definitely Goth…')
  expect(lineFor({ shown: [{ index: 0, name: 'Goth' }], total: 1 })).toMatch(/Weighing/)
  expect(lineFor({ shown: [{ index: 0, name: 'Goth' }], total: 1, verdict: true })).toMatch(/Placing/)
})
