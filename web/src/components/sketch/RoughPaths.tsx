import type { CSSProperties } from 'react'
import type { PathInfo } from '../../lib/rough'

interface RoughPathsProps {
  paths: PathInfo[]
  className?: string
  pathProps?: { pathLength?: number; style?: CSSProperties }
}

/** Render rough.js path data as SVG paths. */
export function RoughPaths({ paths, className, pathProps }: RoughPathsProps) {
  return (
    <g className={className}>
      {paths.map((p, i) => (
        <path
          key={i}
          d={p.d}
          strokeWidth={p.strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          {...pathProps}
          // Colours go in style, not attributes, so CSS variables such as var(--ink) resolve.
          style={{ stroke: p.stroke, fill: p.fill ?? 'none', ...pathProps?.style }}
        />
      ))}
    </g>
  )
}
