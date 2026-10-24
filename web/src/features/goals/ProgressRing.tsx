import { useMemo } from 'react'
import { RoughPaths } from '../../components/sketch/RoughPaths'
import { formatPercent } from '../../lib/format'
import { useLanguage } from '../../lib/i18n'
import { PEN, seedFrom, sketch } from '../../lib/rough'
import { useDrawOn } from '../../lib/useDrawOn'

/** A hand-drawn ring, inked around in proportion to progress toward the goal. */
export function ProgressRing({
  id,
  share,
  size = 88,
}: {
  id: string
  share: number
  size?: number
}) {
  const { t, language } = useLanguage()
  const clamped = Math.min(Math.max(share, 0), 1)
  const c = size / 2
  const r = size - 14
  const { pathProps } = useDrawOn({ duration: 900 })
  const paths = useMemo(() => {
    const seed = seedFrom(id)
    const track = sketch((g) =>
      g.circle(c, c, r, { ...PEN, stroke: 'var(--graphite)', strokeWidth: 1, seed }),
    )
    const done =
      clamped > 0.005
        ? sketch((g) =>
            g.arc(c, c, r, r, -Math.PI / 2, -Math.PI / 2 + clamped * Math.PI * 2, false, {
              ...PEN,
              stroke: clamped >= 1 ? 'var(--leaf)' : 'var(--ink)',
              strokeWidth: 4,
              roughness: 0.8,
              seed: seed + 1,
            }),
          )
        : []
    return { track, done }
  }, [id, c, r, clamped])
  const label = t('progressLabel', { percent: formatPercent(clamped, language) })
  return (
    <svg role="img" aria-label={label} width={size} height={size} className="overflow-visible">
      <RoughPaths paths={paths.track} />
      <RoughPaths paths={paths.done} pathProps={pathProps} />
      <text
        x={c}
        y={c + 6}
        textAnchor="middle"
        className="figure"
        fontSize="17"
        fontWeight="700"
        style={{ fill: 'var(--ink)' }}
      >
        {formatPercent(clamped, language)}
      </text>
    </svg>
  )
}
