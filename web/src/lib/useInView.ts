import { useCallback, useRef, useState } from 'react'

/** True once the element has scrolled into view (and stays true). Used to lazy-draw sketches. */
export function useInView<T extends Element>(
  rootMargin = '120px',
): [(node: T | null) => void, boolean] {
  const [inView, setInView] = useState(typeof IntersectionObserver === 'undefined')
  const observer = useRef<IntersectionObserver | null>(null)

  const ref = useCallback(
    (node: T | null) => {
      observer.current?.disconnect()
      observer.current = null
      if (!node || typeof IntersectionObserver === 'undefined') return
      observer.current = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setInView(true)
            observer.current?.disconnect()
          }
        },
        { rootMargin },
      )
      observer.current.observe(node)
    },
    [rootMargin],
  )

  return [ref, inView]
}
