import { useMemo } from 'react'
import { PEN, seedFrom, sketch } from '../../lib/rough'
import { useDrawOn } from '../../lib/useDrawOn'
import { RoughPaths } from './RoughPaths'

interface Point {
  x: number
  y: number
}

interface SketchArrowProps {
  id: string
  from: Point
  to: Point
  /** Sideways bend of the curve, in px. */
  bend?: number
  className?: string
  delay?: number
}

/** A hand-drawn curved arrow, for use inside an <svg>. It draws itself on mount. */
export function SketchArrow({
  id,
  from,
  to,
  bend = 24,
  className = '',
  delay = 0,
}: SketchArrowProps) {
  const { pathProps } = useDrawOn({ duration: 700, delay })
  const paths = useMemo(() => {
    const seed = seedFrom(id)
    const mid = { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 }
    const angle = Math.atan2(to.y - from.y, to.x - from.x)
    const control = {
      x: mid.x + bend * Math.cos(angle - Math.PI / 2),
      y: mid.y + bend * Math.sin(angle - Math.PI / 2),
    }
    const shaft = sketch((g) =>
      g.curve(
        [
          [from.x, from.y],
          [control.x, control.y],
          [to.x, to.y],
        ],
        { ...PEN, seed },
      ),
    )
    // Arrowhead follows the direction of the last segment of the curve.
    const tip = Math.atan2(to.y - control.y, to.x - control.x)
    const head = [tip + Math.PI - 0.45, tip + Math.PI + 0.45].flatMap((a) =>
      sketch((g) =>
        g.line(to.x, to.y, to.x + 11 * Math.cos(a), to.y + 11 * Math.sin(a), { ...PEN, seed }),
      ),
    )
    return [...shaft, ...head]
  }, [id, from.x, from.y, to.x, to.y, bend])
  return <RoughPaths paths={paths} className={className} pathProps={pathProps} />
}
