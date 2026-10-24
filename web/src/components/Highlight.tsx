import { useEffect, useRef, type ReactNode } from 'react'
import { annotate } from 'rough-notation'
import { prefersReducedMotion } from '../lib/motion'
import { useTheme } from '../lib/theme'

/** Read a palette token: rough-notation needs a real colour, not var(--token). */
function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || 'yellow'
}

/** A hand-drawn highlighter stroke behind its content, redrawn when `redrawKey` changes. */
export function Highlight({ children, redrawKey }: { children: ReactNode; redrawKey?: unknown }) {
  const { theme } = useTheme()
  const ref = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    const element = ref.current
    if (!element) return
    const annotation = annotate(element, {
      type: 'highlight',
      color: cssVar('--highlighter'),
      iterations: 1,
      multiline: true,
      animate: !prefersReducedMotion(),
      animationDuration: 500,
    })
    try {
      annotation.show()
    } catch {
      // No layout (tests): the text is still shown, just not highlighted.
      return
    }
    return () => annotation.remove()
  }, [theme, redrawKey])
  return (
    <span ref={ref} className="relative inline-block text-[#1d3a6b]">
      {children}
    </span>
  )
}
