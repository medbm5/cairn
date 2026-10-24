import { scaleLinear, type ScaleLinear } from 'd3-scale'
import { area, curveMonotoneX, line } from 'd3-shape'
import { useId, useMemo, type ReactNode, type Ref } from 'react'
import { CairnGlyph } from '../components/CairnGlyph'
import { RoughPaths } from '../components/sketch/RoughPaths'
import { formatMoney } from '../lib/format'
import { useLanguage } from '../lib/i18n'
import { PEN, seedFrom, sketch, type PathInfo } from '../lib/rough'
import { useDrawOn } from '../lib/useDrawOn'
import { useElementSize } from '../lib/useElementSize'

export interface ProjectionData {
  months: number[]
  p10: number[]
  p25: number[]
  p50: number[]
  p75: number[]
  p90: number[]
  contributed?: number[]
}

export interface ChartScales {
  x: ScaleLinear<number, number>
  y: ScaleLinear<number, number>
  width: number
  height: number
}

interface ProjectionChartProps {
  /** Stable id: seeds the hand-drawn strokes so they never wobble between renders. */
  id: string
  data: ProjectionData
  targetCents?: number
  /** Rough.js hatching when true; fast smooth paths (e.g. while a slider is dragged) when false. */
  sketchy: boolean
  /** Start the draw-on animation; `instant` shows every line complete. */
  draw?: { active: boolean; instant?: boolean }
  showContributions?: boolean
  height?: number
  /** A text summary for screen readers; the drawing never carries information on its own. */
  summary: string
  /** Hand-drawn annotations (arrows, notes), given the chart's scales. */
  annotations?: (scales: ChartScales) => ReactNode
  /** Where Pebble points: a spot on the median line. */
  medianAnchorRef?: Ref<SVGCircleElement>
}

const PAD = { top: 16, right: 44, bottom: 34, left: 64 }

type Point = [number, number]

function bandPoints(
  months: number[],
  upper: number[],
  lower: number[],
  x: (m: number) => number,
  y: (v: number) => number,
): Point[] {
  const top = months.map((m, i): Point => [x(m), y(upper[i])])
  const bottom = months.map((m, i): Point => [x(m), y(lower[i])]).reverse()
  return [...top, ...bottom]
}

export function ProjectionChart({
  id,
  data,
  targetCents,
  sketchy,
  draw = { active: true },
  showContributions = false,
  height = 320,
  summary,
  annotations,
  medianAnchorRef,
}: ProjectionChartProps) {
  const { language, t } = useLanguage()
  const patternId = useId().replace(/:/g, '')
  const [ref, { width }] = useElementSize<HTMLDivElement>()
  const bandsDraw = useDrawOn({ duration: 1400, active: draw.active })
  const medianDraw = useDrawOn({ duration: 1200, delay: 500, active: draw.active })
  const instant = draw.instant === true

  const scales = useMemo<ChartScales>(() => {
    const maxMonth = data.months[data.months.length - 1] || 1
    const yMax = Math.max(...data.p90, targetCents ?? 0, 1) * 1.08
    return {
      x: scaleLinear()
        .domain([0, maxMonth])
        .range([PAD.left, Math.max(PAD.left + 10, width - PAD.right)]),
      y: scaleLinear()
        .domain([0, yMax])
        .range([height - PAD.bottom, PAD.top]),
      width,
      height,
    }
  }, [data, targetCents, width, height])
  const { x, y } = scales

  const sketched = useMemo(() => {
    if (!sketchy || width === 0) return null
    const seed = seedFrom(id)
    const hatch = (points: Point[], gap: number, s: number): PathInfo[] =>
      sketch((g) =>
        g.polygon(points, {
          ...PEN,
          stroke: 'none',
          fill: 'currentColor',
          fillStyle: 'hachure',
          hachureAngle: -41,
          hachureGap: gap,
          fillWeight: 1.1,
          roughness: 1.4,
          seed: s,
        }),
      )
    const median = data.months.map((m, i): Point => [x(m), y(data.p50[i])])
    return {
      outer: hatch(bandPoints(data.months, data.p90, data.p10, x, y), 9, seed),
      inner: hatch(bandPoints(data.months, data.p75, data.p25, x, y), 4.5, seed + 1),
      median: sketch((g) =>
        g.curve(median, { ...PEN, strokeWidth: 2.6, roughness: 0.7, seed: seed + 2 }),
      ),
      axes: [
        ...sketch((g) =>
          g.line(PAD.left, height - PAD.bottom, width - PAD.right + 8, height - PAD.bottom, {
            ...PEN,
            roughness: 0.6,
            seed: seed + 3,
          }),
        ),
        ...sketch((g) =>
          g.line(PAD.left, height - PAD.bottom, PAD.left, PAD.top, {
            ...PEN,
            roughness: 0.6,
            seed: seed + 4,
          }),
        ),
      ],
    }
  }, [sketchy, width, height, id, data, x, y])

  const smooth = useMemo(() => {
    const band = (upper: number[], lower: number[]) =>
      area<number>()
        .x((m) => x(m))
        .y0((_, i) => y(lower[i]))
        .y1((_, i) => y(upper[i]))
        .curve(curveMonotoneX)(data.months) ?? ''
    const path = (values: number[]) =>
      line<number>()
        .x((m) => x(m))
        .y((_, i) => y(values[i]))
        .curve(curveMonotoneX)(data.months) ?? ''
    return {
      outer: band(data.p90, data.p10),
      inner: band(data.p75, data.p25),
      median: path(data.p50),
      contributed: data.contributed ? path(data.contributed) : '',
    }
  }, [data, x, y])

  const maxMonth = data.months[data.months.length - 1] || 0
  const years = Math.round(maxMonth / 12)
  const yearStep = years > 20 ? 10 : years > 8 ? 5 : years > 3 ? 2 : 1
  const yearTicks = Array.from({ length: Math.floor(years / yearStep) + 1 }, (_, i) => i * yearStep)
  const moneyTicks = y.ticks(4).filter((v) => v > 0)
  const midIndex = Math.floor(data.months.length * 0.62)
  const bandPathProps = instant ? {} : bandsDraw.pathProps
  const medianPathProps = instant ? {} : medianDraw.pathProps

  return (
    <figure ref={ref} className="relative m-0 w-full text-ink">
      <svg
        role="img"
        aria-label={summary}
        width="100%"
        height={height}
        viewBox={`0 0 ${Math.max(width, 1)} ${height}`}
        className="block overflow-visible"
      >
        <defs>
          <pattern
            id={`${patternId}-outer`}
            width="9"
            height="9"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(-41)"
          >
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="9"
              style={{ stroke: 'var(--chart-range)' }}
              strokeWidth="1.1"
            />
          </pattern>
          <pattern
            id={`${patternId}-inner`}
            width="4.5"
            height="4.5"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(-41)"
          >
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="4.5"
              style={{ stroke: 'var(--chart-range)' }}
              strokeWidth="1.1"
            />
          </pattern>
        </defs>

        {width > 0 && (
          <>
            {/* Axes and hand-written labels */}
            {sketched ? (
              <g className="text-graphite">
                <RoughPaths paths={sketched.axes} />
              </g>
            ) : (
              <path
                d={`M${PAD.left} ${PAD.top} V${height - PAD.bottom} H${width - PAD.right + 8}`}
                fill="none"
                stroke="var(--graphite)"
                strokeWidth={1.4}
              />
            )}
            <g className="font-hand" fontSize="13" style={{ fill: 'var(--graphite)' }}>
              {yearTicks.map((year) => (
                <text key={year} x={x(year * 12)} y={height - PAD.bottom + 20} textAnchor="middle">
                  {year === 0 ? t('chartToday') : t('chartYear', { year })}
                </text>
              ))}
              {moneyTicks.map((value) => (
                <text key={value} x={PAD.left - 8} y={y(value) + 4} textAnchor="end">
                  {formatMoney(value, language)}
                </text>
              ))}
            </g>

            {/* Range of outcomes: more ink where outcomes are likelier */}
            <g className="text-chart-range" opacity={0.75}>
              {sketched ? (
                <>
                  <RoughPaths paths={sketched.outer} pathProps={bandPathProps} />
                  <RoughPaths paths={sketched.inner} pathProps={bandPathProps} />
                </>
              ) : (
                <>
                  <path d={smooth.outer} fill={`url(#${patternId}-outer)`} />
                  <path d={smooth.inner} fill={`url(#${patternId}-inner)`} />
                </>
              )}
            </g>

            {showContributions && smooth.contributed && (
              <path
                d={smooth.contributed}
                fill="none"
                stroke="var(--graphite)"
                strokeWidth={1.6}
                strokeDasharray="1 5"
                strokeLinecap="round"
              />
            )}

            {/* Target: a dashed line ending in a small cairn at the goal date */}
            {targetCents !== undefined && (
              <g>
                <line
                  x1={PAD.left}
                  x2={x(maxMonth)}
                  y1={y(targetCents)}
                  y2={y(targetCents)}
                  stroke="var(--chart-target)"
                  strokeWidth={1.8}
                  strokeDasharray="7 6"
                />
                <svg
                  x={x(maxMonth) - 4}
                  y={y(targetCents) - 30}
                  width={32}
                  height={32}
                  overflow="visible"
                >
                  <CairnGlyph className="text-chart-target" />
                </svg>
              </g>
            )}

            {/* Median: the confident pen line */}
            {sketched ? (
              <RoughPaths
                className="text-chart-median"
                paths={sketched.median}
                pathProps={medianPathProps}
              />
            ) : (
              <path
                d={smooth.median}
                fill="none"
                stroke="var(--chart-median)"
                strokeWidth={2.6}
                strokeLinecap="round"
              />
            )}
            <circle
              ref={medianAnchorRef}
              cx={x(data.months[midIndex])}
              cy={y(data.p50[midIndex])}
              r={3}
              fill="transparent"
            />

            {annotations?.(scales)}
          </>
        )}
      </svg>
    </figure>
  )
}
