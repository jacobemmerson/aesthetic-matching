/** The line under the photos while they are processed: what the server has said so far, in words. */

// Phrases by how sure the model is about a photo's top match. {X} is the aesthetic's name.
const BANDS = [
  { min: .7, lead: ['Definitely {X}', 'Unmistakably {X}', 'Strong {X} energy', 'That is {X}'] },
  { min: .3, lead: ['Feeling {X}', 'Getting {X}', 'Leaning {X}', 'Reads as {X}'] },
  { min: 0, lead: ['Picking up a {X} vibe', 'Getting a little {X}', 'A hint of {X}', 'Some {X} in there'] },
]
const MENTION_MIN = .08  // below this a match is noise, not a vibe
// A runner-up worth mentioning gets a tail, worded by its own strength.
const TAILS = [
  { min: .3, tail: [', and some {X}', ', part {X}'] },
  { min: MENTION_MIN, tail: [', with a hint of {X}', ', a touch of {X}'] },
]

const band = (table, p) => table.find((b) => p >= b.min)
const pick = (list, rand) => list[Math.floor(rand() * list.length) % list.length]
const fill = (template, name) => template.replace('{X}', name)

/** One line about a photo from its match distribution, e.g. "Definitely Cottagecore, with a hint of Fairycore…". */
export function phraseFor(matches, names, rand = Math.random) {
  const [top, second] = matches
  const name = (m) => names?.[m.slug] || m.slug
  let line = fill(pick(band(BANDS, top.prob).lead, rand), name(top))
  if (second && second.prob >= MENTION_MIN) line += fill(pick(band(TAILS, second.prob).tail, rand), name(second))
  return line + '…'
}

export function lineFor({ shown = [], total = 0, verdict = false } = {}) {
  if (verdict) return 'Placing you on the globe…'
  if (!shown.length) return 'Reading your photos…'
  const last = shown[shown.length - 1]
  if (shown.length < total) return last.phrase || `${last.name}…`
  return 'Weighing it all up…'
}
