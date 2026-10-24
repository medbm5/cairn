import { useMemo } from 'react'
import { RoughPaths } from '../../components/sketch/RoughPaths'
import { PEN, seedFrom, sketch, type PathInfo } from '../../lib/rough'
import type { GoalType } from './goalTypes'

/** Hand-drawn icons for each kind of goal, in a 64 x 64 box. */
function drawIcon(type: GoalType): PathInfo[] {
  const o = { ...PEN, strokeWidth: 2, seed: seedFrom(`icon-${type}`) }
  switch (type) {
    case 'retirement': // a deck chair under the sun
      return [
        ...sketch((g) => g.circle(48, 14, 14, o)),
        ...sketch((g) => g.line(14, 54, 30, 26, o)),
        ...sketch((g) => g.line(30, 26, 46, 54, o)),
        ...sketch((g) => g.line(22, 42, 44, 42, o)),
        ...sketch((g) => g.line(8, 56, 56, 56, o)),
      ]
    case 'home': // a little house
      return [
        ...sketch((g) => g.rectangle(16, 30, 32, 24, o)),
        ...sketch((g) =>
          g.linearPath(
            [
              [10, 32],
              [32, 12],
              [54, 32],
            ],
            o,
          ),
        ),
        ...sketch((g) => g.rectangle(28, 40, 9, 14, o)),
      ]
    case 'safety_net': // an umbrella
      return [
        ...sketch((g) => g.arc(32, 32, 44, 36, Math.PI, Math.PI * 2, false, o)),
        ...sketch((g) => g.line(10, 32, 54, 32, o)),
        ...sketch((g) => g.line(32, 32, 32, 52, o)),
        ...sketch((g) => g.arc(28, 52, 8, 8, 0, Math.PI, false, o)),
      ]
    case 'studies': // a graduation cap
      return [
        ...sketch((g) =>
          g.polygon(
            [
              [6, 26],
              [32, 14],
              [58, 26],
              [32, 38],
            ],
            o,
          ),
        ),
        ...sketch((g) => g.line(18, 32, 18, 46, o)),
        ...sketch((g) => g.arc(32, 46, 28, 12, 0, Math.PI, false, o)),
        ...sketch((g) => g.line(46, 32, 46, 46, o)),
        ...sketch((g) => g.line(56, 27, 56, 42, o)),
      ]
    case 'other': // a star
      return sketch((g) =>
        g.polygon(
          [
            [32, 8],
            [38, 25],
            [56, 25],
            [42, 36],
            [47, 54],
            [32, 43],
            [17, 54],
            [22, 36],
            [8, 25],
            [26, 25],
          ],
          o,
        ),
      )
  }
}

export function GoalTypeIcon({ type, className = '' }: { type: GoalType; className?: string }) {
  const paths = useMemo(() => drawIcon(type), [type])
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true" className={className}>
      <RoughPaths paths={paths} />
    </svg>
  )
}
