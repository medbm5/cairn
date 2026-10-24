import { scaleLinear } from 'd3-scale'
import { line } from 'd3-shape'
import { useMemo } from 'react'
import { RoughPaths } from '../components/sketch/RoughPaths'
import { formatMoney } from '../lib/format'
import { useLanguage } from '../lib/i18n'
import { PEN, seedFrom, sketch } from '../lib/rough'
import { useDrawOn } from '../lib/useDrawOn'
import { useElementSize } from '../lib/useElementSize'

const PAD = { top: 12, right: 12, bottom: 28, left: 64 }

/** How long the red-pen replay takes to draw. */
export const REPLAY_MS = 2200

/**
 * A crisis replay: the value path drawn in red pen (it draws itself, month by month), and the
 * same mix with rebalancing as a dashed blue line for comparison.
 */
export function StressChart({
  id,
  without,
  withRebalancing,
  height = 240,
}: {
  id: string
  without: number[]
  withRebalancing: number[]
  height?: number
}) {
  const { t, language } = useLanguage()
  const [ref, { width }] = useElementSize<HTMLDivElement>()
  const { pathProps } = useDrawOn({ duration: REPLAY_MS })

  const all = [...without, ...withRebalancing]
  const x = scaleLinear()
    .domain([0, without.length - 1])
    .range([PAD.left, Math.max(PAD.left + 10, width - PAD.right)])
  const y = scaleLinear()
    .domain([Math.min(...all) * 0.95, Math.max(...all) * 1.03])
    .range([height - PAD.bottom, PAD.top])

  const paths = useMemo(
    () =>
      width === 0
        ? []
        : sketch((g) =>
            g.linearPath(
              without.map((v, i) => [x(i), y(v)]),
              {
                ...PEN,
                stroke: 'var(--red-pen)',
                strokeWidth: 2.6,
                roughness: 0.7,
                seed: seedFrom(id),
              },
            ),
          ),
    // x and y derive from the values and width listed here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [width, height, without, withRebalancing, id],
  )
  const rebalanced =
    line<number>()
      .x((_, i) => x(i))
      .y((v) => y(v))(withRebalancing) ?? ''

  const low = Math.min(...without)
  const summary = t('stressChartSummary', {
    months: without.length - 1,
    low: formatMoney(low, language),
    end: formatMoney(without[without.length - 1], language),
  })

  return (
    <div ref={ref} className="w-full">
      <svg
        role="img"
        aria-label={summary}
        width="100%"
        height={height}
        className="block overflow-visible"
      >
        {width > 0 && (
          <>
            <line
              x1={PAD.left}
              x2={width - PAD.right}
              y1={y(without[0])}
              y2={y(without[0])}
              stroke="var(--graphite)"
              strokeDasharray="2 5"
            />
            <text
              x={PAD.left - 8}
              y={y(without[0]) + 4}
              textAnchor="end"
              className="font-hand"
              fontSize="13"
              style={{ fill: 'var(--graphite)' }}
            >
              {formatMoney(without[0], language)}
            </text>
            <text
              x={PAD.left - 8}
              y={y(low) + 4}
              textAnchor="end"
              className="font-hand"
              fontSize="13"
              style={{ fill: 'var(--red-pen)' }}
            >
              {formatMoney(low, language)}
            </text>
            <path
              d={rebalanced}
              fill="none"
              stroke="var(--chart-range)"
              strokeWidth={1.8}
              strokeDasharray="6 5"
            />
            <RoughPaths paths={paths} pathProps={pathProps} />
          </>
        )}
      </svg>
      <ul className="mt-2 flex flex-wrap gap-x-6 text-sm">
        <li>
          <span
            aria-hidden="true"
            className="mr-2 inline-block h-0.5 w-6 bg-red-pen align-middle"
          />
          {t('stressWithout')}
        </li>
        <li>
          <span
            aria-hidden="true"
            className="mr-2 inline-block w-6 border-t-2 border-dashed border-chart-range align-middle"
          />
          {t('stressWith')}
        </li>
      </ul>
    </div>
  )
}
