// eslint-disable-next-line no-unused-vars -- motion used as JSX namespace (motion.div)
import { motion, AnimatePresence } from 'framer-motion'
import { pageVariants } from './variants'

/**
 * Wrap any screen/page with this to get automatic enter/exit animations.
 *
 * Usage:
 *   <AnimatedPage>
 *     <HomeScreen />
 *   </AnimatedPage>
 */
export default function AnimatedPage({ children, className = '' }) {
  return (
    <motion.div
      className={className}
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      style={{ width: '100%' }}
    >
      {children}
    </motion.div>
  )
}

/**
 * AnimatePresence wrapper — place once at the router level.
 * Pass `mode="wait"` to prevent overlap between exiting and entering pages.
 */
export function PageTransitionProvider({ children, locationKey }) {
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div key={locationKey} style={{ width: '100%', minHeight: '100vh' }}>
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
