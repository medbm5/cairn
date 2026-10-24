import { useMemo } from 'react'
import { PEN, seedFrom, sketch } from '../../lib/rough'
import { RoughPaths } from './RoughPaths'

/**
 * Hand-drawn keyboard focus ring. Place inside a `.sketch-focus` element with a known size;
 * CSS shows it only on :focus-visible.
 */
export function SketchRing({ id, width, height }: { id: string; width: number; height: number }) {
  const paths = useMemo(
    () =>
      width > 0
        ? sketch((g) =>
            g.ellipse(width / 2, height / 2, width + 16, height + 14, {
              ...PEN,
              strokeWidth: 2,
              roughness: 1.6,
              seed: seedFrom(`${id}-ring`),
            }),
          )
        : [],
    [id, width, height],
  )
  return (
    <svg
      aria-hidden="true"
      className="sketch-ring pointer-events-none absolute -inset-0 h-full w-full overflow-visible text-ink transition-opacity"
    >
      <RoughPaths paths={paths} />
    </svg>
  )
}
