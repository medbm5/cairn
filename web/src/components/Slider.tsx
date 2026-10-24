import { useId, useMemo } from 'react'
import { PEN, seedFrom, sketch } from '../lib/rough'
import { useElementSize } from '../lib/useElementSize'
import { RoughPaths } from './sketch/RoughPaths'

interface SliderProps {
  label: string
  value: number
  min: number
  max: number
  step?: number
  onChange: (value: number) => void
  /** Called when the person lets go (pointer up or key up): time to re-sketch. */
  onCommit?: (value: number) => void
  /** Human text for the value, read by screen readers and shown beside the label. */
  format: (value: number) => string
  id?: string
}

/**
 * A native range input (keyboard and screen-reader accessible) over a hand-drawn track and a
 * pencil-tip thumb.
 */
export function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
  onCommit,
  format,
  id,
}: SliderProps) {
  const autoId = useId()
  const inputId = id ?? autoId
  const [ref, { width }] = useElementSize<HTMLDivElement>()
  const share = max > min ? (value - min) / (max - min) : 0
  const track = useMemo(
    () =>
      width > 0
        ? sketch((g) =>
            g.line(6, 14, width - 6, 14, {
              ...PEN,
              seed: seedFrom(`${inputId}-track`),
              roughness: 0.9,
            }),
          )
        : [],
    [width, inputId],
  )
  const filled = useMemo(
    () =>
      width > 0 && share > 0.01
        ? sketch((g) =>
            g.line(6, 14, 6 + (width - 12) * share, 14, {
              ...PEN,
              strokeWidth: 3.2,
              seed: seedFrom(`${inputId}-fill`),
              roughness: 0.6,
            }),
          )
        : [],
    [width, share, inputId],
  )
  const commit = () => onCommit?.(value)

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-4">
        <label htmlFor={inputId} className="font-bold">
          {label}
        </label>
        <output htmlFor={inputId} className="figure text-lg font-bold">
          {format(value)}
        </output>
      </div>
      <div ref={ref} className="sketch-focus relative h-8">
        <svg
          aria-hidden="true"
          className="absolute inset-0 h-full w-full overflow-visible text-ink"
        >
          <g className="text-graphite">
            <RoughPaths paths={track} />
          </g>
          <RoughPaths paths={filled} />
          {/* Pencil tip thumb */}
          <g transform={`translate(${6 + Math.max(0, width - 12) * share}, 14)`}>
            <path
              d="M0 0 L-7 -16 L7 -16 Z"
              style={{ fill: 'var(--highlighter)', stroke: 'var(--ink)' }}
              strokeWidth={1.6}
              strokeLinejoin="round"
            />
            <path d="M0 0 L-2.6 -6 L2.6 -6 Z" style={{ fill: 'var(--ink)' }} />
          </g>
        </svg>
        <input
          id={inputId}
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          aria-valuetext={format(value)}
          onChange={(event) => onChange(Number(event.target.value))}
          onPointerUp={commit}
          onKeyUp={commit}
          onBlur={commit}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
        />
      </div>
    </div>
  )
}
