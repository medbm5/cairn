import { useMemo, type ReactNode } from 'react'
import { PEN, seedFrom, sketch } from '../../lib/rough'
import { useDrawOn } from '../../lib/useDrawOn'
import { useElementSize } from '../../lib/useElementSize'
import { RoughPaths } from './RoughPaths'

/** Text with a hand-drawn line under it that draws itself. */
export function SketchUnderline({
  id,
  children,
  className = '',
  color = 'var(--ink)',
}: {
  id: string
  children: ReactNode
  className?: string
  color?: string
}) {
  const [ref, { width, height }] = useElementSize<HTMLSpanElement>()
  const { pathProps } = useDrawOn({ duration: 600 })
  const paths = useMemo(
    () =>
      width > 0
        ? sketch((g) =>
            g.curve(
              [
                [0, height + 3],
                [width * 0.5, height + 5],
                [width, height + 2],
              ],
              { ...PEN, stroke: color, strokeWidth: 2.2, seed: seedFrom(id) },
            ),
          )
        : [],
    [width, height, id, color],
  )
  return (
    <span ref={ref} className={`relative inline-block ${className}`}>
      {children}
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full overflow-visible"
      >
        <RoughPaths paths={paths} pathProps={pathProps} />
      </svg>
    </span>
  )
}
