import { useCallback, useRef, useState } from 'react'

export interface Size {
  width: number
  height: number
}

/** Measure an element with ResizeObserver (zero size where it is unavailable, as in tests). */
export function useElementSize<T extends Element>(): [(node: T | null) => void, Size] {
  const [size, setSize] = useState<Size>({ width: 0, height: 0 })
  const observer = useRef<ResizeObserver | null>(null)

  // React calls the ref with null on unmount, which disconnects the observer.
  const ref = useCallback((node: T | null) => {
    observer.current?.disconnect()
    observer.current = null
    if (!node || typeof ResizeObserver === 'undefined') return
    observer.current = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize((prev) =>
        Math.round(prev.width) === Math.round(width) &&
        Math.round(prev.height) === Math.round(height)
          ? prev
          : { width, height },
      )
    })
    observer.current.observe(node)
  }, [])

  return [ref, size]
}
