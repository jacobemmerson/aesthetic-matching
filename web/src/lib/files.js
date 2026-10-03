export const MIN_FILES = 3
export const MAX_FILES = 10
export const MAX_BYTES = 5_000_000

export function acceptFiles(existing, incoming) {
  const reasons = []
  const accepted = [...existing]
  const seen = new Set(existing.map((f) => `${f.name}:${f.size}`))
  let overflow = 0
  for (const f of incoming) {
    if (!f.type.startsWith('image/')) { reasons.push(`${f.name} is not an image`); continue }
    if (f.size > MAX_BYTES) { reasons.push(`${f.name} is over 5 MB`); continue }
    const key = `${f.name}:${f.size}`
    if (seen.has(key)) continue
    if (accepted.length >= MAX_FILES) { overflow++; continue }
    seen.add(key); accepted.push(f)
  }
  if (overflow) reasons.push(`only ${MAX_FILES} photos allowed, ${overflow} more left out`)
  return { accepted, notice: reasons.join('. ') }
}
