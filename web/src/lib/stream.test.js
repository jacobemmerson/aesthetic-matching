import { expect, it } from 'vitest'
import { ndjson } from './stream.js'

const stream = (chunks) => new ReadableStream({ start(c) { chunks.forEach((s) => c.enqueue(new TextEncoder().encode(s))); c.close() } })
const collect = async (body) => { const out = []; for await (const m of ndjson(body)) out.push(m); return out }

it('yields objects per line, across chunk boundaries, and a trailing line without a newline', async () => {
  expect(await collect(stream(['{"a":1}\n{"b":', '2}\n\n', '{"c":3}']))).toEqual([{ a: 1 }, { b: 2 }, { c: 3 }])
})

it('keeps multi-byte characters split across chunks', async () => {
  const bytes = new TextEncoder().encode('{"s":"é"}\n')
  const body = new ReadableStream({ start(c) { c.enqueue(bytes.slice(0, 6)); c.enqueue(bytes.slice(6)); c.close() } })
  expect(await collect(body)).toEqual([{ s: 'é' }])
})
