import { useMemo } from 'react'
import { Figure } from '../components/Figure'
import { ASSET_ORDER, type AssetClass, type Weights } from '../lib/assets'
import { RoughPaths } from '../components/sketch/RoughPaths'
import { formatPercent } from '../lib/format'
import { useLanguage, type StringKey } from '../lib/i18n'
import { PEN, seedFrom, sketch, type RoughOptions } from '../lib/rough'
import { useDrawOn } from '../lib/useDrawOn'
import { useElementSize } from '../lib/useElementSize'

// Each asset class gets its own pen texture, so the bar reads without colour.
const TEXTURES: Record<AssetClass, RoughOptions> = {
  global_equity: { fillStyle: 'hachure', hachureGap: 4, hachureAngle: -41 },
  emerging_equity: { fillStyle: 'cross-hatch', hachureGap: 6, hachureAngle: -41 },
  euro_gov_bonds: { fillStyle: 'hachure', hachureGap: 9, hachureAngle: 49 },
  money_market: { fillStyle: 'dots', hachureGap: 8 },
}

interface AllocationBarProps {
  id: string
  weights: Weights
  /** Draw the bar stroke by stroke (on reveal). */
  drawOn?: boolean
  /** Smooth blocks instead of rough sketching, e.g. while scrubbing. */
  sketchy?: boolean
  height?: number
}

/** The allocation as a hand-drawn stacked bar, with an exact legend. */
export function AllocationBar({
  id,
  weights,
  drawOn = false,
  sketchy = true,
  height = 64,
}: AllocationBarProps) {
  const { t, language } = useLanguage()
  const [ref, { width }] = useElementSize<HTMLDivElement>()
  const { pathProps } = useDrawOn({ duration: 1400, active: drawOn })
  const segments = useMemo(() => {
    const usable = Math.max(width - 4, 0)
    const widths = ASSET_ORDER.map((asset) => usable * (weights[asset] ?? 0))
    return ASSET_ORDER.map((asset, i) => ({
      asset,
      x: 2 + widths.slice(0, i).reduce((sum, w) => sum + w, 0),
      w: widths[i],
    }))
  }, [weights, width])

  const paths = useMemo(() => {
    if (!sketchy || width === 0) return []
    return segments
      .filter((s) => s.w > 1)
      .flatMap((s) =>
        sketch((g) =>
          g.rectangle(s.x, 4, s.w, height - 8, {
            ...PEN,
            fill: 'currentColor',
            fillWeight: 1.2,
            seed: seedFrom(`${id}-${s.asset}`),
            ...TEXTURES[s.asset],
          }),
        ),
      )
  }, [segments, sketchy, width, height, id])

  const parts = ASSET_ORDER.filter((a) => (weights[a] ?? 0) > 0)
    .map((a) => `${t(`asset_${a}` as StringKey)} ${formatPercent(weights[a] ?? 0, language)}`)
    .join(', ')

  return (
    <figure className="m-0">
      <div ref={ref} className="w-full text-ink">
        <svg
          role="img"
          aria-label={t('allocationSummary', { parts })}
          width="100%"
          height={height}
          className="block overflow-visible"
        >
          {sketchy ? (
            <RoughPaths paths={paths} pathProps={drawOn ? pathProps : undefined} />
          ) : (
            segments.map((s, i) => (
              <rect
                key={s.asset}
                x={s.x}
                y={4}
                width={Math.max(s.w, 0)}
                height={height - 8}
                fill="currentColor"
                opacity={0.75 - i * 0.17}
                stroke="var(--ink)"
                strokeWidth={1.5}
                style={{ transition: 'x 120ms linear, width 120ms linear' }}
              />
            ))
          )}
        </svg>
      </div>
      <figcaption>
        <ul className="mt-3 grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">
          {ASSET_ORDER.map((asset) => (
            <li key={asset} className="flex items-baseline justify-between gap-3">
              <span>{t(`asset_${asset}` as StringKey)}</span>
              <Figure kind="percent" value={weights[asset] ?? 0} className="font-bold" />
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  )
}
