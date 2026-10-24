import { useEffect } from 'react'
import { REPLAY_MS, StressChart } from '../../charts/StressChart'
import { SketchButton } from '../../components/sketch/SketchButton'
import { formatPercent } from '../../lib/format'
import { useLanguage, type StringKey } from '../../lib/i18n'
import { prefersReducedMotion } from '../../lib/motion'
import { useStressTest, type Scenario } from '../../lib/queries'
import { usePebble } from '../../pebble/PebbleProvider'

const SCENARIOS: Scenario[] = ['gfc_2008', 'covid_2020', 'rates_2022']
const SCENARIO_NAMES: Record<Scenario, { en: string; fr: string }> = {
  gfc_2008: { en: 'the 2008 financial crisis', fr: 'la crise financière de 2008' },
  covid_2020: { en: 'the 2020 Covid shock', fr: 'le choc du Covid en 2020' },
  rates_2022: { en: 'the 2022 rate shock', fr: 'le choc de taux de 2022' },
}

/**
 * "Replay 2008" and friends: the value path is drawn in red pen while Pebble looks worried,
 * then Pebble explains the result. The outcome is also stated in a sentence.
 */
export function StressTestPanel({ goalId, anchorId }: { goalId: number; anchorId: string }) {
  const { t, language } = useLanguage()
  const pebble = usePebble()
  const replay = useStressTest(goalId)
  const result = replay.data

  useEffect(() => {
    if (!result) return
    pebble.pointAt(anchorId)
    pebble.setState('worried')
    const timer = window.setTimeout(
      () => {
        pebble.setState('idle')
        pebble.say({
          topic: 'stress_test',
          anchorId,
          facts: {
            scenario: result.scenario,
            start_cents: result.start_cents,
            max_drawdown: result.without_rebalancing.max_drawdown,
            max_drawdown_rebalanced: result.with_rebalancing.max_drawdown,
            months_to_recover: result.without_rebalancing.months_to_recover,
          },
        })
      },
      prefersReducedMotion() ? 0 : REPLAY_MS,
    )
    return () => window.clearTimeout(timer)
    // Once per replay result.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result])

  const plain = result?.without_rebalancing
  const recovery =
    plain && plain.months_to_recover !== null && plain.months_to_recover !== undefined
      ? t('stressRecovered', { months: plain.months_to_recover })
      : t('stressNotRecovered')

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-3">
        {SCENARIOS.map((scenario) => (
          <SketchButton
            key={scenario}
            sketchId={`replay-${scenario}`}
            variant={replay.variables === scenario ? 'primary' : 'secondary'}
            disabled={replay.isPending}
            onClick={() => replay.mutate(scenario)}
          >
            {t(`replay_${scenario}` as StringKey)}
          </SketchButton>
        ))}
      </div>
      {replay.isError && (
        <p role="alert" className="font-bold text-red-pen">
          {t('stressError')}
        </p>
      )}
      {result && plain && (
        <>
          <StressChart
            key={`${result.scenario}-${replay.submittedAt}`}
            id={`stress-${result.scenario}`}
            without={plain.values}
            withRebalancing={result.with_rebalancing.values}
          />
          <p aria-live="polite">
            {t('stressSentence', {
              scenario: SCENARIO_NAMES[result.scenario][language],
              drop: formatPercent(plain.max_drawdown, language),
              recovery,
              dropRebalanced: formatPercent(result.with_rebalancing.max_drawdown, language),
            })}
          </p>
        </>
      )}
    </div>
  )
}
