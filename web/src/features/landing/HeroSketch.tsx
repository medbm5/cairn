import { useEffect, useState } from 'react'
import { ProjectionChart } from '../../charts/ProjectionChart'
import { Figure } from '../../components/Figure'
import { Slider } from '../../components/Slider'
import { SketchArrow } from '../../components/sketch/SketchArrow'
import { formatDuration, formatMoney, formatPercent } from '../../lib/format'
import { useLanguage } from '../../lib/i18n'
import { useReducedMotion } from '../../lib/motion'
import { useInView } from '../../lib/useInView'
import { useSettled } from '../../lib/useSettled'
import { usePebble, usePebbleAnchor } from '../../pebble/PebbleProvider'
import example from './example.json'

const DEFAULT_STOP = example.stops.findIndex((s) => s.monthly_contribution_cents === 400_00)

/**
 * The signature moment: Pebble walks onto the page and sketches a projection for an example
 * goal, then points at the median. The slider reshapes the drawing live. The sequence lasts
 * about 2.5 s and is skipped by scrolling, clicking or a key press.
 */
export function HeroSketch() {
  const { t, language } = useLanguage()
  const pebble = usePebble()
  const reduced = useReducedMotion()
  const [stopIndex, setStopIndex] = useState(DEFAULT_STOP)
  const [intro, setIntro] = useState<'running' | 'note' | 'done'>(reduced ? 'done' : 'running')
  const [heroRef, heroVisible] = useInView<HTMLElement>('0px')
  const chartAnchor = usePebbleAnchor('hero-chart')
  const medianAnchor = usePebbleAnchor('hero-median')
  const settled = useSettled(stopIndex, 150)
  // Sketching costs main-thread time: start right after first paint, not during it.
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const idle = window.requestIdleCallback ?? ((cb: () => void) => window.setTimeout(cb, 1))
    const cancel = window.cancelIdleCallback ?? window.clearTimeout
    const handle = idle(() => setReady(true))
    return () => cancel(handle)
  }, [])

  const stop = example.stops[stopIndex]
  const target = example.target_cents
  const last = stop.months.length - 1

  // The intro: walk in and sketch, then point at the median with a handwritten note.
  useEffect(() => {
    if (intro === 'done') return
    const skip = () => setIntro('done')
    const events = ['wheel', 'touchmove', 'keydown', 'pointerdown'] as const
    events.forEach((name) => window.addEventListener(name, skip, { once: true, passive: true }))
    pebble.pointAt('hero-chart')
    pebble.setState('sketch')
    const noteTimer = window.setTimeout(() => setIntro('note'), 1700)
    const doneTimer = window.setTimeout(() => setIntro('done'), 2500)
    return () => {
      events.forEach((name) => window.removeEventListener(name, skip))
      window.clearTimeout(noteTimer)
      window.clearTimeout(doneTimer)
    }
    // Runs once for the intro; `pebble` changes identity on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intro === 'done'])

  useEffect(() => {
    if (intro === 'running') return
    pebble.setState('idle')
    pebble.pointAt(heroVisible ? 'hero-median' : null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intro, heroVisible])

  // Leave Pebble at home when navigating away.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => () => pebble.pointAt(null), [])

  const summary = t('chartSummary', {
    years: formatDuration(example.horizon_months, language),
    p50: formatMoney(stop.p50[last], language),
    p10: formatMoney(stop.p10[last], language),
    p90: formatMoney(stop.p90[last], language),
    target: formatMoney(target, language),
    chance: formatPercent(stop.success_probability ?? 0, language),
  })

  return (
    <section ref={heroRef} className="grid gap-8 pt-6 lg:grid-cols-12 lg:items-center">
      <div className="lg:col-span-4">
        <h1>{t('heroHeadline')}</h1>
        <p className="mt-4 max-w-md text-lg">
          {t('heroIntro', {
            initial: formatMoney(example.initial_cents, language),
            target: formatMoney(target, language),
            years: formatDuration(example.horizon_months, language),
          })}
        </p>
        <div className="mt-8 max-w-sm">
          <Slider
            label={t('monthlySavings')}
            value={stopIndex}
            min={0}
            max={example.stops.length - 1}
            onChange={(value) => {
              setIntro('done')
              setStopIndex(value)
            }}
            format={(i) => formatMoney(example.stops[i].monthly_contribution_cents, language)}
          />
        </div>
        <p className="mt-6">
          <span className="block text-graphite">
            {t('heroChance', { target: formatMoney(target, language) })}
          </span>
          <Figure
            kind="percent"
            value={stop.success_probability ?? 0}
            className="text-4xl font-bold"
          />
        </p>
      </div>

      <div ref={chartAnchor} className="min-h-[360px] lg:col-span-8">
        {ready && (
          <ProjectionChart
            id="hero"
            data={stop}
            targetCents={target}
            sketchy={settled}
            draw={{ active: true, instant: intro === 'done' }}
            height={360}
            summary={summary}
            medianAnchorRef={medianAnchor}
            annotations={({ x, y }) => {
              if (intro === 'running') return null
              const at = Math.floor(last * 0.55)
              const mx = x(stop.months[at])
              const my = y(stop.p50[at])
              return (
                <g className="text-ink">
                  <SketchArrow
                    id="hero-note-arrow"
                    from={{ x: mx - 44, y: my - 62 }}
                    to={{ x: mx - 4, y: my - 8 }}
                    bend={18}
                  />
                  <text
                    x={mx - 50}
                    y={my - 70}
                    textAnchor="end"
                    className="font-hand"
                    fontSize="17"
                    // A paper-coloured halo keeps the note legible over the hatching.
                    style={{
                      fill: 'var(--ink)',
                      stroke: 'var(--paper)',
                      strokeWidth: 5,
                      paintOrder: 'stroke',
                    }}
                  >
                    {t('heroNote')}
                  </text>
                </g>
              )
            }}
          />
        )}
      </div>
    </section>
  )
}
