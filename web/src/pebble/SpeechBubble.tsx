import { useMemo, type ReactNode } from 'react'
import { PEN, seedFrom, sketch } from '../lib/rough'
import { useElementSize } from '../lib/useElementSize'
import { RoughPaths } from '../components/sketch/RoughPaths'

/** A hand-drawn speech bubble with a small tail pointing down toward Pebble. */
export function SpeechBubble({
  id,
  children,
  tail = 'right',
}: {
  id: string
  children: ReactNode
  tail?: 'left' | 'right'
}) {
  const [ref, { width, height }] = useElementSize<HTMLDivElement>()
  const paths = useMemo(() => {
    if (width < 10) return []
    const seed = seedFrom(id)
    const tx = tail === 'right' ? width - 46 : 46
    return [
      ...sketch((g) =>
        g.rectangle(2, 2, width - 4, height - 4, {
          ...PEN,
          seed,
          fill: 'var(--paper)',
          fillStyle: 'solid',
        }),
      ),
      ...sketch((g) =>
        g.polygon(
          [
            [tx - 10, height - 3],
            [tx + (tail === 'right' ? 18 : -18), height + 16],
            [tx + 10, height - 3],
          ],
          { ...PEN, seed: seed + 1, fill: 'var(--paper)', fillStyle: 'solid' },
        ),
      ),
    ]
  }, [id, width, height, tail])

  return (
    <div ref={ref} className="relative text-ink">
      <svg aria-hidden="true" className="absolute inset-0 h-full w-full overflow-visible">
        <RoughPaths paths={paths} />
      </svg>
      {/* Long explanations scroll inside the bubble; Lenis must leave the wheel to it. */}
      <div
        data-lenis-prevent
        className="relative max-h-[min(26rem,60vh)] overflow-y-auto overscroll-contain p-4"
      >
        {children}
      </div>
    </div>
  )
}
