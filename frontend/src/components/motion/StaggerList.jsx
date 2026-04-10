import { motion } from 'framer-motion'
import { staggerContainer, staggerItem } from './variants'

/**
 * Renders a list where each child animates in with a stagger delay.
 *
 * Usage:
 *   <StaggerList>
 *     {items.map(item => <div key={item.id}>…</div>)}
 *   </StaggerList>
 */
export default function StaggerList({ children, className = '', as = 'div' }) {
  const Tag = motion[as] || motion.div

  return (
    <Tag
      className={className}
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
    >
      {children && (Array.isArray(children) ? children : [children]).map((child, i) => (
        <motion.div key={i} variants={staggerItem}>
          {child}
        </motion.div>
      ))}
    </Tag>
  )
}
