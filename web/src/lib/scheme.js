import { useEffect, useState } from 'react'

export const PHONE = '(max-width: 799px)'

export function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const onChange = () => setMatches(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [query])
  return matches
}

export const useColorScheme = () => (useMediaQuery('(prefers-color-scheme: dark)') ? 'dark' : 'light')
