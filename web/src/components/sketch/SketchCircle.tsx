import { useMemo } from 'react'
import { PEN, seedFrom, sketch } from '../../lib/rough'
import { useDrawOn } from '../../lib/useDrawOn'
import { RoughPaths } from './RoughPaths'

interface SketchCircleProps {
  id: string
  cx: number
  cy: number
  width: number
  height?: number
  className?: string
  delay?: number
}

/** A hand-drawn loop around something, for use inside an <svg>. */
export function SketchCircle({
  id,
  cx,
  cy,
  width,
  height = width,
  className = '',
  delay = 0,
}: SketchCircleProps) {
  const { pathProps } = useDrawOn({ duration: 600, delay })
  const paths = useMemo(
    () =>
      sketch((g) =>
        g.ellipse(cx, cy, width, height, { ...PEN, seed: seedFrom(id), roughness: 1.5 }),
      ),
    [id, cx, cy, width, height],
  )
  return <RoughPaths paths={paths} className={className} pathProps={pathProps} />
}
