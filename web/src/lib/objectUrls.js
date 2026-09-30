import { useEffect, useRef, useState } from 'react'

export function syncObjectUrls(prev, files, { create, revoke }) {
  const next = new Map()
  for (const f of files) next.set(f, prev.get(f) ?? create(f))
  for (const [f, url] of prev) if (!next.has(f)) revoke(url)
  return next
}

const urlApi = { create: (f) => URL.createObjectURL(f), revoke: (u) => URL.revokeObjectURL(u) }

export function useObjectUrls(files) {
  const current = useRef(new Map())
  const [urls, setUrls] = useState(current.current)
  useEffect(() => {
    current.current = syncObjectUrls(current.current, files, urlApi)
    setUrls(current.current)
  }, [files])
  useEffect(() => () => {
    syncObjectUrls(current.current, [], urlApi)
    current.current = new Map()
  }, [])
  return urls
}
