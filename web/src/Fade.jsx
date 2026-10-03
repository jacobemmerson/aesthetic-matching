import { motion } from 'framer-motion'

/** Opacity enter/exit for anything that appears or disappears; wrap in AnimatePresence for the exit. */
export default function Fade({ as = 'div', duration = .25, ...props }) {
  const Tag = motion[as]
  return <Tag initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration }} {...props} />
}
