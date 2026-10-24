import { useEffect, useRef, type ReactNode } from 'react'
import { annotate } from 'rough-notation'
import { usePebble } from './PebbleProvider'

/**
 * A jargon word with a hand-drawn dotted underline. Tapping it makes Pebble explain it.
 */
export function Term({
  term,
  children,
  anchorId,
}: {
  term: string
  children: ReactNode
  anchorId?: string
}) {
  const pebble = usePebble()
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const element = ref.current
    if (!element || typeof element.getBoundingClientRect !== 'function') return
    const annotation = annotate(element, {
      type: 'underline',
      color: 'var(--graphite)',
      strokeWidth: 1.5,
      padding: 1,
      iterations: 1,
      // Dotted via CSS (.term-wrap), which rules out rough-notation's dash-based draw-in.
      animate: false,
    })
    // jsdom has no layout; rough-notation would throw there.
    try {
      annotation.show()
    } catch {
      return
    }
    return () => annotation.remove()
  }, [])

  return (
    <span className="term-wrap">
      <button
        type="button"
        onClick={() => pebble.say({ term, anchorId })}
        className="inline p-0 text-left font-[inherit] text-[inherit] [color:inherit]"
      >
        <span ref={ref}>{children}</span>
      </button>
    </span>
  )
}
