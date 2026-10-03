import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

/** The selected aesthetic's description, laid out in the verdict column in full. */
export default function Drawer({ node, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <AnimatePresence>
      {node && (
        <motion.aside className="drawer" key={node.slug} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: .25 }}>
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
