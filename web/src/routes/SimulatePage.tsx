import { useMemo, useState } from 'react'
import { ProjectionChart, type ChartScales } from '../charts/ProjectionChart'
import { Figure } from '../components/Figure'
import { Highlight } from '../components/Highlight'
import { Skeleton } from '../components/Skeleton'
import { Slider } from '../components/Slider'
import { SketchArrow } from '../components/sketch/SketchArrow'
import { SketchButton } from '../components/sketch/SketchButton'
import { useToast } from '../components/Toast'
import { SolverPanel } from '../features/solver/SolverPanel'
import { formatDuration, formatMoney, formatPercent } from '../lib/format'
import { useLanguage, type StringKey } from '../lib/i18n'
import {
  solveSimulation,
  useSimulation,
  type RiskProfile,
  type SimulationRequest,
  type Solution,
  type SolverOption,
} from '../lib/queries'
import { useDebounced, useSettled } from '../lib/useSettled'
import { PebbleInline } from '../pebble/PebbleInline'
import { usePebble, usePebbleAnchor, type TourStep } from '../pebble/PebbleProvider'
import { useTour } from '../pebble/useTour'

const PROFILES: RiskProfile[] = ['prudent', 'moderate', 'balanced', 'dynamic', 'bold']
// The sliders' steps and caps: the solver's answers land on them, so "Use this plan" fits.
const MONTHLY_STEP = 25_00
const MONTHLY_MAX = 3_000_00
const TARGET_STEP = 5_000_00
const SOLVE_AT = 0.8

interface Preview {
  option: SolverOption
  solution: Solution
  /** The inputs the options were worked out for; a preview of older inputs is ignored. */
  key: string
}

interface Inputs {
  initial: number // cents
  monthly: number // cents
  years: number
  target: number // cents
  profile: RiskProfile
}

export function SimulatePage() {
  const { t, language } = useLanguage()
  const pebble = usePebble()
  const toast = useToast()
  const [inputs, setInputs] = useState<Inputs>({
    initial: 5_000_00,
    monthly: 300_00,
    years: 15,
    target: 100_000_00,
    profile: 'balanced',
  })
  const set =
    <K extends keyof Inputs>(key: K) =>
    (value: Inputs[K]) =>
      setInputs((current) => ({ ...current, [key]: value }))

  // Requests go out 150 ms after the last change; the previous drawing stays meanwhile.
  const debounced = useDebounced(inputs, 150)
  const settled = useSettled(inputs, 150)
  const request = useMemo<SimulationRequest>(
    () => ({
      initial_cents: debounced.initial,
      monthly_contribution_cents: debounced.monthly,
      horizon_months: debounced.years * 12,
      target_cents: debounced.target,
      profile: debounced.profile,
      glide_path: true,
      paths: 2000,
      seed: 42,
    }),
    [debounced],
  )
  const simulation = useSimulation(request)
  const inputsKey = JSON.stringify(debounced)
  const [previewState, setPreview] = useState<Preview | null>(null)
  const preview = previewState?.key === inputsKey ? previewState : null
  const previewRequest = useMemo<SimulationRequest | null>(() => {
    if (!preview) return null
    const { option, solution } = preview
    return {
      ...request,
      monthly_contribution_cents:
        option.lever === 'contribution' ? option.value : request.monthly_contribution_cents,
      horizon_months: option.lever === 'horizon' ? option.value : request.horizon_months,
      target_cents: option.lever === 'target' ? option.value : request.target_cents,
      seed: solution.seed,
      paths: solution.paths,
    }
  }, [preview, request])
  const previewSimulation = useSimulation(previewRequest)
  // While a solver option is previewed, the chart shows the plan with that option applied.
  const previewing = previewRequest !== null && previewSimulation.data !== undefined
  const shownRequest = previewing ? previewRequest : request
  const data = previewing ? previewSimulation.data : simulation.data
  const baseChance = simulation.data?.success_probability ?? 0

  const solve = () =>
    solveSimulation({
      initial_cents: debounced.initial,
      monthly_contribution_cents: debounced.monthly,
      horizon_months: debounced.years * 12,
      target_cents: debounced.target,
      profile: debounced.profile,
      target_probability: SOLVE_AT,
      contribution_step_cents: MONTHLY_STEP,
      horizon_step_months: 12,
      target_step_cents: TARGET_STEP,
      max_contribution_cents: MONTHLY_MAX,
    })
  const apply = (option: SolverOption) => {
    setPreview(null)
    setInputs((current) => ({
      ...current,
      monthly: option.lever === 'contribution' ? option.value : current.monthly,
      years: option.lever === 'horizon' ? option.value / 12 : current.years,
      target: option.lever === 'target' ? option.value : current.target,
    }))
    toast.show(t('solverApplied'), 'success')
  }

  const slidersAnchor = usePebbleAnchor('sim-sliders')
  const chartAnchor = usePebbleAnchor('sim-chart')
  const medianAnchor = usePebbleAnchor('sim-median')
  const chanceAnchor = usePebbleAnchor('sim-chance')
  const whatAnchor = usePebbleAnchor('sim-what')

  const steps = useMemo<TourStep[]>(
    () => [
      { anchorId: 'sim-sliders', text: t('tourSimSliders') },
      { anchorId: 'sim-chart', text: t('tourSimChart') },
      { anchorId: 'sim-chance', text: t('tourSimChance') },
      { anchorId: 'sim-what', text: t('tourSimWhat') },
    ],
    [t],
  )
  const replayTour = useTour('simulate', steps, data !== undefined)

  const last = data ? data.months.length - 1 : 0
  const chance = data?.success_probability ?? 0
  const summary = data
    ? t('chartSummary', {
        years: formatDuration(data.months[last], language),
        p50: formatMoney(data.p50[last], language),
        p10: formatMoney(data.p10[last], language),
        p90: formatMoney(data.p90[last], language),
        target: formatMoney(shownRequest.target_cents ?? 0, language),
        chance: formatPercent(chance, language),
      })
    : ''

  const explain = () => {
    if (!data) return
    pebble.say({
      topic: 'projection',
      anchorId: 'sim-median',
      facts: {
        profile: shownRequest.profile,
        target_cents: shownRequest.target_cents,
        horizon_months: shownRequest.horizon_months,
        monthly_contribution_cents: shownRequest.monthly_contribution_cents,
        p10_cents: data.p10[last],
        p50_cents: data.p50[last],
        p90_cents: data.p90[last],
        success_probability: chance,
      },
    })
  }

  const annotations = ({ x, y }: ChartScales) => {
    if (!data || !settled) return null
    const end = x(data.months[last])
    const label = (text: string, ty: number) => (
      <text
        x={end - 92}
        y={ty}
        textAnchor="end"
        className="font-hand"
        fontSize="15"
        style={{ fill: 'var(--ink)', stroke: 'var(--paper)', strokeWidth: 5, paintOrder: 'stroke' }}
      >
        {text}
      </text>
    )
    const p90y = y(data.p90[last])
    const p10y = y(data.p10[last])
    return (
      <g className="text-ink">
        {label(t('simGreatMarket'), p90y - 22)}
        <SketchArrow
          id="sim-p90"
          from={{ x: end - 88, y: p90y - 26 }}
          to={{ x: end - 6, y: p90y }}
          bend={-14}
        />
        {label(t('simToughMarket'), p10y + 38)}
        <SketchArrow
          id="sim-p10"
          from={{ x: end - 88, y: p10y + 34 }}
          to={{ x: end - 6, y: p10y + 2 }}
          bend={14}
        />
      </g>
    )
  }

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1>{t('simTitle')}</h1>
          <p className="mt-2 max-w-xl">{t('simIntro')}</p>
        </div>
        <SketchButton sketchId="sim-tour" variant="quiet" onClick={replayTour}>
          {t('showMeAround')}
        </SketchButton>
      </div>

      <div className="grid gap-8 lg:grid-cols-12">
        <div ref={slidersAnchor} className="flex flex-col gap-6 lg:col-span-4">
          <Slider
            label={t('simInitial')}
            value={inputs.initial}
            min={0}
            max={100_000_00}
            step={500_00}
            onChange={set('initial')}
            format={(v) => formatMoney(v, language)}
          />
          <Slider
            label={t('simMonthly')}
            value={inputs.monthly}
            min={0}
            max={MONTHLY_MAX}
            step={MONTHLY_STEP}
            onChange={set('monthly')}
            format={(v) => formatMoney(v, language)}
          />
          <Slider
            label={t('simHorizon')}
            value={inputs.years}
            min={1}
            max={40}
            onChange={set('years')}
            format={(v) => formatDuration(v * 12, language)}
          />
          <Slider
            label={t('simTarget')}
            value={inputs.target}
            min={5_000_00}
            max={1_000_000_00}
            step={TARGET_STEP}
            onChange={set('target')}
            format={(v) => formatMoney(v, language)}
          />
          <fieldset>
            <legend className="mb-2 font-bold">{t('simProfile')}</legend>
            <div className="flex flex-wrap gap-2">
              {PROFILES.map((profile) => (
                <label
                  key={profile}
                  className={`flex min-h-11 cursor-pointer items-center border-2 px-3 ${
                    inputs.profile === profile
                      ? 'border-ink bg-highlighter/40 font-bold'
                      : 'border-dashed border-graphite/60'
                  }`}
                >
                  <input
                    type="radio"
                    name="profile"
                    value={profile}
                    checked={inputs.profile === profile}
                    onChange={() => set('profile')(profile)}
                    className="sr-only"
                  />
                  {t(`profile_${profile}` as StringKey)}
                </label>
              ))}
            </div>
          </fieldset>
        </div>

        <div className="flex flex-col gap-4 lg:col-span-8">
          <div ref={chanceAnchor} className="flex flex-wrap items-end justify-between gap-4">
            <p>
              <span className="block text-graphite">
                {t('simChance', {
                  target: formatMoney(shownRequest.target_cents ?? inputs.target, language),
                })}
              </span>
              {data ? (
                <Highlight redrawKey={`${chance}-${settled}`}>
                  <Figure kind="percent" value={chance} className="text-4xl font-bold" />
                </Highlight>
              ) : (
                <span className="text-4xl">…</span>
              )}
            </p>
            <div ref={whatAnchor}>
              <SketchButton
                sketchId="sim-what"
                variant="primary"
                onClick={explain}
                disabled={!data}
              >
                {t('simWhat')}
              </SketchButton>
            </div>
          </div>

          <div ref={chartAnchor} aria-busy={simulation.isFetching}>
            {simulation.isError && !data ? (
              <div role="alert" className="flex flex-col items-start gap-3 py-10">
                <p>{t('simError')}</p>
                <SketchButton sketchId="sim-retry" onClick={() => simulation.refetch()}>
                  {t('tryAgain')}
                </SketchButton>
              </div>
            ) : data ? (
              <ProjectionChart
                id="simulator"
                data={data}
                targetCents={shownRequest.target_cents ?? undefined}
                sketchy={
                  previewing
                    ? !previewSimulation.isPlaceholderData
                    : settled && !simulation.isPlaceholderData
                }
                draw={{ active: true }}
                showContributions
                height={380}
                summary={summary}
                annotations={annotations}
                medianAnchorRef={medianAnchor}
              />
            ) : (
              <Skeleton id="sim-loading" lines={6} className="py-10" />
            )}
          </div>
          {data && <p className="sr-only">{summary}</p>}
          {simulation.data && baseChance < SOLVE_AT && (
            <SolverPanel
              key={inputsKey}
              id="sim-solver"
              anchorId="sim-chart"
              solve={solve}
              onPreview={(option, solution) =>
                setPreview(option && solution ? { option, solution, key: inputsKey } : null)
              }
              onApply={apply}
            />
          )}
          <ul className="grid gap-1 text-sm text-graphite sm:grid-cols-2">
            <li className="flex items-baseline gap-2">
              <span
                aria-hidden="true"
                className="inline-block h-3 w-5 shrink-0 bg-chart-range/60"
              />
              {t('simLegendRange')}
            </li>
            <li className="flex items-baseline gap-2">
              <span
                aria-hidden="true"
                className="inline-block w-5 shrink-0 -translate-y-1 border-t-[3px] border-chart-median"
              />
              {t('simLegendMedian')}
            </li>
            <li className="flex items-baseline gap-2">
              <span
                aria-hidden="true"
                className="inline-block w-5 shrink-0 -translate-y-1 border-t-2 border-dashed border-chart-target"
              />
              {t('simLegendTarget')}
            </li>
            <li className="flex items-baseline gap-2">
              <span
                aria-hidden="true"
                className="inline-block w-5 shrink-0 -translate-y-1 border-t-2 border-dotted border-graphite"
              />
              {t('simLegendContributed')}
            </li>
          </ul>
          <PebbleInline anchorId="sim-median" />
        </div>
      </div>
    </section>
  )
}
