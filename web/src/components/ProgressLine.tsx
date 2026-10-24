import { useMemo } from 'react'
import { PEN, seedFrom, sketch } from '../lib/rough'
import { useElementSize } from '../lib/useElementSize'
import { RoughPaths } from './sketch/RoughPaths'

/** A hand-drawn progress line: a faint pencil track, inked up to the current step. */
export function ProgressLine({
  id,
  value,
  max,
  label,
}: {
  id: string
  value: number
  max: number
  label: string
}) {
  const [ref, { width }] = useElementSize<HTMLDivElement>()
  const share = max > 0 ? value / max : 0
  const paths = useMemo(() => {
    if (width === 0) return { track: [], done: [] }
    return {
      track: sketch((g) =>
        g.line(4, 10, width - 4, 10, { ...PEN, seed: seedFrom(`${id}-track`), roughness: 0.8 }),
      ),
      done:
        share > 0
          ? sketch((g) =>
              g.line(4, 10, 4 + (width - 8) * share, 10, {
                ...PEN,
                strokeWidth: 4,
                roughness: 0.9,
                seed: seedFrom(`${id}-done-${value}`),
              }),
            )
          : [],
    }
  }, [width, share, id, value])
  return (
    <div
      ref={ref}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      className="h-5 w-full"
    >
      <svg aria-hidden="true" className="h-full w-full overflow-visible">
        <g className="text-graphite" opacity={0.6}>
          <RoughPaths paths={paths.track} />
        </g>
        <g className="text-ink">
          <RoughPaths paths={paths.done} />
        </g>
      </svg>
    </div>
  )
}
