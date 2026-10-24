import type { ReactNode } from 'react'
import { seedFrom } from '../../lib/rough'
import { SketchBox } from './SketchBox'

/**
 * A separate object on the page (a goal, for example): a paper card slightly rotated, with a
 * taped corner. Use sparingly.
 */
export function PaperCard({
  id,
  children,
  className = '',
}: {
  id: string
  children: ReactNode
  className?: string
}) {
  const tilt = seedFrom(id) % 2 === 0 ? 0.5 : -0.5
  return (
    <div className={`relative ${className}`} style={{ transform: `rotate(${tilt}deg)` }}>
      <span
        aria-hidden="true"
        className="absolute -top-3 left-6 z-10 h-6 w-20 -rotate-3 bg-highlighter/45 shadow-sm"
      />
      <SketchBox id={id} className="bg-paper p-5 shadow-[2px_3px_0_rgba(0,0,0,0.06)]">
        {children}
      </SketchBox>
    </div>
  )
}
