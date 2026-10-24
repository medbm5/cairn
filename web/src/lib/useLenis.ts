import Lenis from 'lenis'
import { useEffect } from 'react'
import { useReducedMotion } from './motion'

/** Lenis smooth scrolling while the calling page is mounted; off with reduced motion. */
export function useLenis(): void {
  const reduced = useReducedMotion()
  useEffect(() => {
    if (reduced) return
    const lenis = new Lenis()
    let frame = 0
    const raf = (time: number) => {
      lenis.raf(time)
      frame = requestAnimationFrame(raf)
    }
    frame = requestAnimationFrame(raf)
    return () => {
      cancelAnimationFrame(frame)
      lenis.destroy()
    }
  }, [reduced])
}
