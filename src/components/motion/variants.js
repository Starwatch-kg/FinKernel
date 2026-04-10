/**
 * Framer Motion reusable variants
 * Usage: <motion.div {...fadeUp} />  or  variants={fadeUp.variants} initial="hidden" animate="visible"
 */

// ── Page transitions ──────────────────────────────────────────────────────────
export const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.25, 0.1, 0.25, 1] } },
  exit:    { opacity: 0, y: -8, transition: { duration: 0.2 } },
}

// ── Card appear ───────────────────────────────────────────────────────────────
export const cardVariants = {
  hidden:  { opacity: 0, scale: 0.95, y: 12 },
  visible: {
    opacity: 1, scale: 1, y: 0,
    transition: { duration: 0.3, ease: [0.34, 1.56, 0.64, 1] },
  },
}

// ── Stagger container ─────────────────────────────────────────────────────────
export const staggerContainer = {
  hidden:  { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.05 },
  },
}

export const staggerItem = {
  hidden:  { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
}

// ── Slide in from side ────────────────────────────────────────────────────────
export const slideInLeft = {
  hidden:  { opacity: 0, x: -24 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.35, ease: 'easeOut' } },
}

export const slideInRight = {
  hidden:  { opacity: 0, x: 24 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.35, ease: 'easeOut' } },
}

// ── Scale popup ───────────────────────────────────────────────────────────────
export const popupVariants = {
  hidden:  { opacity: 0, scale: 0.85 },
  visible: {
    opacity: 1, scale: 1,
    transition: { type: 'spring', stiffness: 400, damping: 25 },
  },
  exit:    { opacity: 0, scale: 0.9, transition: { duration: 0.15 } },
}

// ── Bounce in (achievements / success) ───────────────────────────────────────
export const bounceIn = {
  hidden:  { opacity: 0, scale: 0.3 },
  visible: {
    opacity: 1, scale: 1,
    transition: { type: 'spring', stiffness: 500, damping: 18 },
  },
}

// ── Progress bar ──────────────────────────────────────────────────────────────
export const progressBar = (width) => ({
  initial: { scaleX: 0 },
  animate: { scaleX: width / 100, transition: { duration: 0.7, ease: 'easeOut', delay: 0.2 } },
})

// ── Ticker tape (number counter) ──────────────────────────────────────────────
export const numberChange = {
  initial:  { y: -10, opacity: 0 },
  animate:  { y: 0, opacity: 1 },
  exit:     { y: 10, opacity: 0 },
  transition: { duration: 0.2 },
}

// ── Shake (wrong answer) ──────────────────────────────────────────────────────
export const shakeVariants = {
  shake: {
    x: [0, -8, 8, -6, 6, -4, 4, 0],
    transition: { duration: 0.4 },
  },
}

// ── Pulse (highlight accent) ─────────────────────────────────────────────────
export const pulseVariants = {
  pulse: {
    scale: [1, 1.04, 1],
    transition: { duration: 0.6, repeat: Infinity, repeatType: 'loop' },
  },
}
