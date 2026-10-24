import { useMemo, type ReactNode } from 'react'
import { PEN, seedFrom, sketch, type RoughOptions } from '../../lib/rough'
import { useElementSize } from '../../lib/useElementSize'
import { RoughPaths } from './RoughPaths'

interface SketchBoxProps {
  /** Stable id for the rough.js seed. */
  id: string
  children: ReactNode
  className?: string
  options?: RoughOptions
  as?: 'div' | 'section' | 'article'
}

/** A container with a hand-drawn rectangle outline. */
export function SketchBox({
  id,
  children,
  className = '',
  options,
  as: Tag = 'div',
}: SketchBoxProps) {
  const [ref, { width, height }] = useElementSize<HTMLDivElement>()
  const paths = useMemo(
    () =>
      width > 8 && height > 8
        ? sketch((g) =>
            g.rectangle(3, 3, width - 6, height - 6, { ...PEN, seed: seedFrom(id), ...options }),
          )
        : [],
    [width, height, id, options],
  )
  return (
    <Tag ref={ref} className={`relative ${className}`}>
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full overflow-visible"
      >
        <RoughPaths paths={paths} />
      </svg>
      <div className="relative">{children}</div>
    </Tag>
  )
}
