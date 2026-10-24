import { usePebble, useInlineSlot } from './PebbleProvider'
import { SpeechContent } from './SpeechContent'

/**
 * Where an explanation appears in the page flow when Pebble is quiet. Messages whose anchorId
 * matches this slot render here as a plain panel instead of a speech bubble.
 */
export function PebbleInline({ anchorId }: { anchorId: string }) {
  useInlineSlot(anchorId)
  const { quiet, current } = usePebble()
  if (!quiet || !current || current.request.anchorId !== anchorId) return null
  return (
    <aside aria-live="polite" className="my-4 border-l-4 border-ink bg-paper/80 p-4">
      <SpeechContent handwritten={false} />
    </aside>
  )
}
