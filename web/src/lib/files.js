export const MAX_FILES = 10
export const MAX_BYTES = 5_000_000
export function acceptFiles(existing, incoming) {
  return { accepted: [...existing, ...incoming].slice(0, MAX_FILES), notice: '' }
}
