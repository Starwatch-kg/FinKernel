import { useEffect, useRef, useState } from 'react'
// eslint-disable-next-line no-unused-vars -- motion used as JSX namespace (motion.div)
import { motion, useMotionValue, animate } from 'framer-motion'

/**
 * Animates a number from its previous value to a new value.
 *
 * Usage:
 *   <AnimatedNumber value={progress.xp} format={n => `${n} XP`} />
 */
export default function AnimatedNumber({ value, format = (n) => Math.round(n).toLocaleString('ru-RU'), duration = 1 }) {
  const motionValue = useMotionValue(value)
  const [display, setDisplay] = useState(format(value))
  const prevValue = useRef(value)

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration,
      ease: 'easeOut',
      onUpdate: (latest) => setDisplay(format(latest)),
    })
    prevValue.current = value
    return controls.stop
  }, [value, duration, format, motionValue])

  return <span>{display}</span>
}

/**
 * Animated progress bar driven by Framer Motion.
 */
export function AnimatedProgressBar({ value, max = 100, className = '', color = 'var(--accent)' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))

  return (
    <div
      className={className}
      style={{
        width: '100%',
        height: 6,
        background: 'rgba(0,0,0,0.08)',
        borderRadius: 99,
        overflow: 'hidden',
      }}
    >
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.7, ease: 'easeOut', delay: 0.1 }}
        style={{ height: '100%', background: color, borderRadius: 99 }}
      />
    </div>
  )
}
