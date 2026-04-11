import { useEffect, useState } from 'react'
// eslint-disable-next-line no-unused-vars -- motion used as JSX namespace (motion.circle etc)
import { motion, AnimatePresence } from 'framer-motion'

const COLORS = ['#ffdd2d', '#21a038', '#2196f3', '#ff5722', '#9c27b0', '#00bcd4']
const SHAPES = ['circle', 'rect', 'triangle']

function Piece({ x, color, shape, size, delay, duration }) {
  const style =
    shape === 'circle'
      ? { borderRadius: '50%', width: size, height: size }
      : shape === 'rect'
      ? { width: size, height: size * 0.6 }
      : { width: 0, height: 0,
          borderLeft: `${size / 2}px solid transparent`,
          borderRight: `${size / 2}px solid transparent`,
          borderBottom: `${size}px solid ${color}`,
          background: 'transparent' }

  return (
    <motion.div
      style={{
        position: 'fixed',
        top: -20,
        left: `${x}%`,
        background: shape !== 'triangle' ? color : undefined,
        zIndex: 9999,
        pointerEvents: 'none',
        ...style,
      }}
      initial={{ y: -20, opacity: 1, rotate: 0 }}
      animate={{
        y: window.innerHeight + 40,
        opacity: [1, 1, 0],
        rotate: Math.random() > 0.5 ? 720 : -720,
        x: [(Math.random() - 0.5) * 80, (Math.random() - 0.5) * 160],
      }}
      transition={{ duration, delay, ease: 'easeIn' }}
    />
  )
}

/**
 * Burst of confetti on achievement unlock / lesson complete.
 *
 * Usage:
 *   const [show, setShow] = useState(false)
 *   <Confetti active={show} onDone={() => setShow(false)} />
 */
export default function Confetti({ active, count = 60, onDone }) {
  const [pieces, setPieces] = useState([])

  useEffect(() => {
    if (!active) return
    const newPieces = Array.from({ length: count }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      shape: SHAPES[Math.floor(Math.random() * SHAPES.length)],
      size: 6 + Math.random() * 10,
      delay: Math.random() * 0.5,
      duration: 1.5 + Math.random() * 1.5,
    }))
    setPieces(newPieces)

    const maxDuration = Math.max(...newPieces.map(p => p.delay + p.duration)) * 1000 + 100
    const timer = setTimeout(() => {
      setPieces([])
      onDone?.()
    }, maxDuration)
    return () => clearTimeout(timer)
  }, [active, count, onDone])

  return (
    <AnimatePresence>
      {pieces.map((p) => (
        <Piece key={p.id} {...p} />
      ))}
    </AnimatePresence>
  )
}
