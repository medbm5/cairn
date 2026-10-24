import { useCallback, useEffect } from 'react'
import { readStorage, writeStorage } from '../lib/storage'
import { usePebble, type TourStep } from './PebbleProvider'

/**
 * A short guided tour of a screen, shown once on the first visit (remembered in localStorage)
 * and replayable from a "Show me around" button.
 */
export function useTour(screenId: string, steps: TourStep[], ready = true): () => void {
  const pebble = usePebble()
  const key = `cairn.tour.${screenId}`

  const replay = useCallback(() => pebble.tour(steps), [pebble, steps])

  useEffect(() => {
    if (!ready || pebble.quiet || readStorage(key) === 'seen') return
    // Give the page a moment to lay out so Pebble can find its anchors.
    const timer = window.setTimeout(() => {
      writeStorage(key, 'seen')
      pebble.tour(steps)
    }, 900)
    return () => window.clearTimeout(timer)
    // Only on first mount of the screen, once ready.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready])

  return replay
}
