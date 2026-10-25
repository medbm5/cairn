import { useRef, useState } from 'react'
import { AllocationBar } from '../../charts/AllocationBar'
import { Figure } from '../../components/Figure'
import { Slider } from '../../components/Slider'
import { blendWeights } from '../../lib/assets'
import { formatDate, formatMoney } from '../../lib/format'
import { useLanguage } from '../../lib/i18n'
import type { GlidePath, Goal, Simulation } from '../../lib/queries'
import { readStorage, writeStorage } from '../../lib/storage'
import { useSettled } from '../../lib/useSettled'
import { usePebble } from '../../pebble/PebbleProvider'

const EXPLAINED_KEY = 'cairn.explained.glide_path'
// The scrubber moves in hundredths of a year so it glides; it snaps to a whole year on release.
const FINE_STEP = 0.01

/**
 * A scrubber over the years to the goal. Dragging morphs the allocation bar along the glide
 * path and shows the projection at that year. Pebble explains the glide path on first use.
 */
export function TimeMachine({
  goal,
  glidePath,
  simulation,
  anchorId,
}: {
  goal: Goal
  glidePath: GlidePath
  simulation: Simulation
  anchorId: string
}) {
  const { t, language } = useLanguage()
  const pebble = usePebble()
  // `position` is in years and moves continuously while dragging; `year` is the whole year shown.
  const [position, setPosition] = useState(0)
  const year = Math.round(position)
  const settled = useSettled(position, 150)
  const explained = useRef(readStorage(EXPLAINED_KEY) === 'seen')
  const points = glidePath.points
  const lastIndex = points.length - 1
  const below = Math.min(Math.floor(position), lastIndex)
  const above = Math.min(below + 1, lastIndex)
  const weights = blendWeights(points[below].weights, points[above].weights, position - below)

  const month = Math.min(year * 12, simulation.months[simulation.months.length - 1])
  const index = simulation.months.indexOf(month)
  const date = new Date()
  date.setMonth(date.getMonth() + month)

  const onChange = (next: number) => {
    setPosition(next)
    if (explained.current) return
    explained.current = true
    writeStorage(EXPLAINED_KEY, 'seen')
    const last = points[points.length - 1]
    pebble.say({
      topic: 'glide_path',
      anchorId,
      facts: {
        profile: goal.profile,
        years_remaining: Math.round(points[0].months_remaining / 12),
        equity_share_now: points[0].equity_share,
        equity_share_at_goal: last.equity_share,
      },
    })
  }

  return (
    <div className="flex flex-col gap-5">
      <Slider
        label={t('timeMachineYear')}
        value={position}
        min={0}
        max={lastIndex}
        step={FINE_STEP}
        keyStep={1}
        onChange={onChange}
        onCommit={(value) => setPosition(Math.round(value))}
        format={(value) => {
          const y = Math.round(value)
          return y === 0
            ? t('chartToday')
            : t('timeMachineValue', {
                year: y,
                date: formatDate(
                  new Date(new Date().setMonth(new Date().getMonth() + y * 12)).toISOString(),
                  language,
                ),
              })
        }}
      />
      <AllocationBar id="time-machine" weights={weights} sketchy={settled} />
      {index >= 0 && (
        <p>
          <span className="block text-sm text-graphite">
            {formatDate(date.toISOString(), language)}
          </span>
          <span className="text-2xl font-bold">
            <Figure kind="money" value={simulation.p50[index]} />
          </span>
          {year > 0 && (
            <span className="block text-sm">
              {t('timeMachineRange', {
                p50: formatMoney(simulation.p50[index], language),
                p10: formatMoney(simulation.p10[index], language),
                p90: formatMoney(simulation.p90[index], language),
              })}
            </span>
          )}
        </p>
      )}
    </div>
  )
}
