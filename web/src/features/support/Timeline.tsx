import { useEffect, useMemo, useRef } from 'react'
import { annotate } from 'rough-notation'
import { Figure } from '../../components/Figure'
import { RoughPaths } from '../../components/sketch/RoughPaths'
import { formatMoney } from '../../lib/format'
import { useLanguage, type StringKey } from '../../lib/i18n'
import { prefersReducedMotion } from '../../lib/motion'
import type { TimelineEvent } from '../../lib/queries'
import { PEN, seedFrom, sketch } from '../../lib/rough'
import { useTheme } from '../../lib/theme'
import { useElementSize } from '../../lib/useElementSize'
import { dayLabel, groupByMonth, monthLabel } from './events'

const LINE_X = 11

// Each kind of event gets its own marker shape and colour; its name is always written beside it.
const MARKER_COLOR: Record<string, string> = {
  deposit: 'var(--leaf)',
  fee: 'var(--red-pen)',
  rebalance: 'var(--graphite)',
}

function markerColor(event: TimelineEvent): string {
  if (event.type === 'market') {
    return event.amount_cents < 0 ? 'var(--red-pen)' : 'var(--chart-range)'
  }
  return MARKER_COLOR[event.type] ?? 'var(--ink)'
}

/** A small sketched marker: a filled dot for money in or out, a hollow one for the rest. */
function Marker({ event }: { event: TimelineEvent }) {
  const paths = useMemo(() => {
    const seed = seedFrom(`event-${event.id}`)
    const filled = event.type === 'deposit' || event.type === 'fee'
    if (event.type === 'rebalance') {
      return sketch((g) =>
        g.rectangle(5, 5, 12, 12, { ...PEN, seed, roughness: 0.9, fill: 'var(--paper)' }),
      )
    }
    return sketch((g) =>
      g.circle(11, 11, 13, {
        ...PEN,
        seed,
        roughness: 1,
        fill: filled ? 'currentColor' : 'var(--paper)',
        fillStyle: 'solid',
      }),
    )
  }, [event.id, event.type])
  return (
    <svg aria-hidden="true" width={22} height={22} className="shrink-0 overflow-visible">
      <g style={{ color: markerColor(event) }}>
        <RoughPaths paths={paths} />
      </g>
    </svg>
  )
}

/** rough-notation highlighter behind a matching event, drawn while `active`. */
function useEventHighlight(active: boolean) {
  const ref = useRef<HTMLSpanElement>(null)
  const { theme } = useTheme()
  useEffect(() => {
    const element = ref.current
    if (!active || !element) return
    const color =
      getComputedStyle(document.documentElement).getPropertyValue('--highlighter').trim() ||
      'yellow'
    const annotation = annotate(element, {
      type: 'highlight',
      color,
      iterations: 1,
      multiline: true,
      animate: !prefersReducedMotion(),
      animationDuration: 500,
    })
    try {
      annotation.show()
    } catch {
      // No layout (tests): the row is still marked as highlighted for assistive tech.
      return
    }
    return () => annotation.remove()
  }, [active, theme])
  return ref
}

function EventRow({
  event,
  highlighted,
  onSelect,
}: {
  event: TimelineEvent
  highlighted: boolean
  onSelect: (event: TimelineEvent, element: HTMLElement) => void
}) {
  const { t, language } = useLanguage()
  const highlightRef = useEventHighlight(highlighted)
  const moved = event.type === 'rebalance'
  return (
    <li data-event-id={event.id} data-highlighted={highlighted} className="relative">
      <button
        type="button"
        onClick={(e) => onSelect(event, e.currentTarget)}
        className="flex min-h-11 w-full items-start gap-3 py-1.5 text-left"
      >
        <Marker event={event} />
        <span
          ref={highlightRef}
          className={`flex min-w-0 flex-1 flex-wrap items-baseline justify-between gap-x-3 ${
            // On the highlighter every word is notebook ink, in both themes, so it stays legible.
            highlighted ? 'relative text-[#1d3a6b] [&_*]:!text-[#1d3a6b]' : ''
          }`}
        >
          <span className="min-w-0">
            <span className="figure mr-2 text-sm text-graphite">{dayLabel(event, language)}</span>
            <span className="underline decoration-dotted decoration-2 underline-offset-4">
              {t(`entry_${event.type}` as StringKey)}
            </span>
            <span className="block text-sm text-graphite">
              {event.goal.name} ·{' '}
              {t('supportGoalValue', {
                amount: formatMoney(event.goal_value_after_cents, language),
              })}
            </span>
          </span>
          <Figure
            kind="money"
            value={event.amount_cents}
            decimals={2}
            className={
              moved
                ? 'text-graphite'
                : event.amount_cents < 0
                  ? 'font-bold text-red-pen'
                  : 'font-bold'
            }
          />
        </span>
      </button>
    </li>
  )
}

/**
 * The client's account as one hand-drawn timeline: a pen line down the page, a sketched marker
 * per event, figures in crisp type. Selecting an event asks Pebble to explain it.
 */
export function Timeline({
  events,
  highlighted,
  onSelect,
}: {
  events: TimelineEvent[]
  highlighted: ReadonlySet<number>
  onSelect: (event: TimelineEvent, element: HTMLElement) => void
}) {
  const { language } = useLanguage()
  const [ref, { height }] = useElementSize<HTMLDivElement>()
  const line = useMemo(
    () =>
      height > 20
        ? sketch((g) =>
            g.line(LINE_X, 8, LINE_X, height - 8, {
              ...PEN,
              roughness: 0.8,
              seed: seedFrom('support-timeline'),
            }),
          )
        : [],
    [height],
  )

  return (
    <div ref={ref} className="relative">
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 left-0 h-full w-6 overflow-visible text-graphite"
      >
        <RoughPaths paths={line} />
      </svg>
      {groupByMonth(events).map(([key, monthEvents]) => (
        <section key={key} aria-label={monthLabel(key, language)} className="mb-3">
          <h3 className="relative ml-8 bg-paper/80 text-lg">{monthLabel(key, language)}</h3>
          <ul>
            {monthEvents.map((event) => (
              <EventRow
                key={event.id}
                event={event}
                highlighted={highlighted.has(event.id)}
                onSelect={onSelect}
              />
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
