// eslint-disable-next-line no-unused-vars -- motion used as JSX namespace (motion.div)
import { motion } from 'framer-motion'
import { cardVariants } from './variants'

/**
 * Drop-in replacement for a plain <div> card with entrance animation.
 *
 * Usage:
 *   <AnimatedCard delay={0.1} className="my-card">…</AnimatedCard>
 */
export default function AnimatedCard({ children, className = '', delay = 0, onClick }) {
  return (
    <motion.div
      className={className}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover={{ y: -2, boxShadow: '0 8px 32px rgba(0,0,0,0.10)' }}
      whileTap={onClick ? { scale: 0.98 } : undefined}
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
      transition={{ delay }}
    >
      {children}
    </motion.div>
  )
}
