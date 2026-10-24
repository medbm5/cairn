import { useEffect, useState, type CSSProperties } from 'react'
import { useReducedMotion } from './motion'

interface DrawOnOptions {
  /** Length of the stroke animation in ms. */
  duration?: number
  delay?: number
  /** Start drawing only when true (e.g. when the element scrolls into view). */
  active?: boolean
}

interface DrawOn {
  /** True once the line is fully drawn. Immediately true with reduced motion. */
  done: boolean
  /** Spread on an SVG path: it draws itself, as if sketched with a pencil. */
  pathProps: { pathLength?: number; style?: CSSProperties }
}

/**
 * The signature "line draws itself" animation, via stroke-dashoffset on a path normalised with
 * pathLength=1. With prefers-reduced-motion, lines appear complete straight away.
 */
export function useDrawOn({
  duration = 1200,
  delay = 0,
  active = true,
}: DrawOnOptions = {}): DrawOn {
  const reduced = useReducedMotion()
  const [started, setStarted] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (reduced || !active) return
    let frame = 0
    // Two frames so the browser paints the hidden state before the transition starts.
    frame = requestAnimationFrame(() => {
      frame = requestAnimationFrame(() => setStarted(true))
    })
    const timer = window.setTimeout(() => setDone(true), delay + duration)
    return () => {
      cancelAnimationFrame(frame)
      window.clearTimeout(timer)
    }
  }, [reduced, active, delay, duration])

  if (reduced) return { done: true, pathProps: {} }
  return {
    done,
    pathProps: {
      pathLength: 1,
      style: {
        strokeDasharray: 1,
        strokeDashoffset: started ? 0 : 1,
        transition: `stroke-dashoffset ${duration}ms cubic-bezier(0.45, 0.05, 0.35, 1) ${delay}ms`,
      },
    },
  }
}
