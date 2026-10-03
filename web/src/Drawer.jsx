import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

export default function Drawer({ node, onClose }) {
  const axis = window.matchMedia('(max-width: 799px)').matches ? 'y' : 'x'
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <AnimatePresence>
      {node && (
        <motion.aside className="drawer" key={node.slug}
          initial={{ [axis]: '100%', opacity: 0 }} animate={{ [axis]: 0, opacity: 1 }} exit={{ [axis]: '100%', opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}>
          <button className="close" aria-label="close" onClick={onClose}>×</button>
          <h2>{node.name}</h2>
          {node.other_names && <p className="aliases">{node.other_names}</p>}
          <p className="desc">{node.description}</p>
          {node.key_values && <p className="values"><span>Values</span> {node.key_values}</p>}
        </motion.aside>
      )}
    </AnimatePresence>
  )
}
