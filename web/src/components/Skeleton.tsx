import { useMemo } from 'react'
import { useLanguage } from '../lib/i18n'
import { seedFrom, sketch } from '../lib/rough'
import { RoughPaths } from './sketch/RoughPaths'

/** A loading placeholder drawn as scribbled pencil lines. */
export function Skeleton({
  id,
  lines = 3,
  className = '',
}: {
  id: string
  lines?: number
  className?: string
}) {
  const { t } = useLanguage()
  const paths = useMemo(
    () =>
      Array.from({ length: lines }, (_, i) =>
        sketch((g) =>
          g.line(4, 12 + i * 26, i === lines - 1 ? 180 : 300, 12 + i * 26, {
            stroke: 'var(--graphite)',
            strokeWidth: 6,
            roughness: 2.2,
            seed: seedFrom(`${id}-${i}`),
          }),
        ),
      ).flat(),
    [id, lines],
  )
  return (
    <div className={`text-graphite ${className}`}>
      <svg
        aria-hidden="true"
        viewBox={`0 0 310 ${lines * 26}`}
        className="h-auto w-full max-w-sm animate-pulse opacity-40"
      >
        <RoughPaths paths={paths} />
      </svg>
      <span className="sr-only">{t('loading')}</span>
    </div>
  )
}
