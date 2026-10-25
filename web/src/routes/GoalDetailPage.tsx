import { useMemo, useState, type ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { AllocationBar } from '../charts/AllocationBar'
import { ProjectionChart } from '../charts/ProjectionChart'
import { Figure } from '../components/Figure'
import { Highlight } from '../components/Highlight'
import { Skeleton } from '../components/Skeleton'
import { SketchButton, SketchLink } from '../components/sketch/SketchButton'
import { useToast } from '../components/Toast'
import { DepositForm } from '../features/goals/DepositForm'
import { LedgerTable } from '../features/goals/LedgerTable'
import { RebalanceList } from '../features/goals/RebalanceList'
import { StressTestPanel } from '../features/goals/StressTestPanel'
import { TimeMachine } from '../features/goals/TimeMachine'
import { SolverPanel } from '../features/solver/SolverPanel'
import { ApiError } from '../lib/api'
import { formatDate, formatDuration, formatMoney, formatPercent } from '../lib/format'
import { useLanguage, type StringKey } from '../lib/i18n'
import {
  solveGoal,
  useBalance,
  useEntries,
  useGlidePath,
  useGoal,
  useProjection,
  useRebalances,
  useSimulation,
  useUpdateGoal,
  type SimulationRequest,
  type Solution,
  type SolverOption,
} from '../lib/queries'
import { PebbleInline } from '../pebble/PebbleInline'
import { usePebbleAnchor, type TourStep } from '../pebble/PebbleProvider'
import { useTour } from '../pebble/useTour'

const SOLVE_AT = 0.8

function Panel({
  title,
  children,
  anchor,
  id,
}: {
  title: string
  children: ReactNode
  anchor?: (element: Element | null) => void
  id: string
}) {
  return (
    <section ref={anchor} aria-labelledby={id} className="flex flex-col gap-4">
      <h2 id={id}>{title}</h2>
      {children}
      <PebbleInline anchorId={id} />
    </section>
  )
}

export function GoalDetailPage() {
  const { t, language } = useLanguage()
  const goalId = Number(useParams().id)
  const goal = useGoal(goalId)
  const balance = useBalance(goalId)
  const entries = useEntries(goalId)
  const rebalances = useRebalances(goalId)
  const projection = useProjection(goalId)
  const glidePath = useGlidePath(goal.data?.profile, projection.data?.horizon_months)
  const updateGoal = useUpdateGoal(goalId)
  const toast = useToast()

  // A solver option being previewed: the chart shows the plan with that option applied.
  const [preview, setPreview] = useState<{ option: SolverOption; solution: Solution } | null>(null)
  const previewRequest = useMemo<SimulationRequest | null>(() => {
    if (!preview || !goal.data || !projection.data) return null
    const { option, solution } = preview
    return {
      initial_cents: projection.data.start_cents,
      monthly_contribution_cents:
        option.lever === 'contribution' ? option.value : goal.data.monthly_contribution_cents,
      horizon_months: option.lever === 'horizon' ? option.value : projection.data.horizon_months,
      target_cents: option.lever === 'target' ? option.value : goal.data.target_cents,
      profile: goal.data.profile,
      glide_path: true,
      seed: solution.seed,
      paths: solution.paths,
    }
  }, [preview, goal.data, projection.data])
  const previewSimulation = useSimulation(previewRequest)
  const projectionAnchor = usePebbleAnchor('goal-projection')

  const balanceAnchor = usePebbleAnchor('goal-balance')
  const timeAnchor = usePebbleAnchor('goal-time')
  const stressAnchor = usePebbleAnchor('goal-stress')
  const ledgerAnchor = usePebbleAnchor('goal-ledger')
  const steps = useMemo<TourStep[]>(
    () => [
      { anchorId: 'goal-balance', text: t('tourGoalBalance') },
      { anchorId: 'goal-time', text: t('tourGoalTime') },
      { anchorId: 'goal-stress', text: t('tourGoalStress') },
      { anchorId: 'goal-ledger', text: t('tourGoalLedger') },
    ],
    [t],
  )
  const replayTour = useTour('goal', steps, goal.isSuccess && glidePath.isSuccess)

  if (goal.isPending) return <Skeleton id="goal-loading" lines={5} />
  if (goal.isError) {
    const missing = goal.error instanceof ApiError && goal.error.status === 404
    return (
      <section role="alert" className="flex max-w-lg flex-col items-start gap-4">
        <p>{missing ? t('goalNotFound') : t('errorBody')}</p>
        {missing ? (
          <SketchLink sketchId="goal-back" to="/goals">
            {t('backToGoals')}
          </SketchLink>
        ) : (
          <SketchButton sketchId="goal-retry" onClick={() => goal.refetch()}>
            {t('tryAgain')}
          </SketchButton>
        )}
      </section>
    )
  }

  const g = goal.data
  const total = balance.data?.total_cents ?? 0
  const startingWeights = glidePath.data?.points[0]?.weights

  const previewing = previewRequest !== null && previewSimulation.data !== undefined
  const shown = previewing ? previewSimulation.data : projection.data?.simulation
  const shownTarget = previewRequest?.target_cents ?? g.target_cents
  const chance = shown?.success_probability ?? 0
  const lastIndex = shown ? shown.months.length - 1 : 0
  const projectionSummary = shown
    ? t('chartSummary', {
        years: formatDuration(shown.months[lastIndex], language),
        p50: formatMoney(shown.p50[lastIndex], language),
        p10: formatMoney(shown.p10[lastIndex], language),
        p90: formatMoney(shown.p90[lastIndex], language),
        target: formatMoney(shownTarget, language),
        chance: formatPercent(chance, language),
      })
    : ''
  const baseChance = projection.data?.simulation.success_probability ?? 0

  const applyPlan = (option: SolverOption) => {
    const change =
      option.lever === 'contribution'
        ? { monthly_contribution_cents: option.value }
        : option.lever === 'horizon'
          ? { target_date: option.target_date! }
          : { target_cents: option.value }
    updateGoal.mutate(change, {
      onSuccess: () => {
        setPreview(null)
        toast.show(t('solverApplied'), 'success')
      },
      onError: () => toast.show(t('solverApplyError'), 'error'),
    })
  }

  return (
    <div className="flex flex-col gap-12">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-graphite">{t(`goalType_${g.type}` as StringKey)}</p>
          <h1>{g.name}</h1>
          <p className="mt-1 text-lg">
            <Figure kind="money" value={g.target_cents} className="font-bold" />{' '}
            {t('goalBy', { date: formatDate(g.target_date, language) })}
            {projection.data && (
              <span className="text-graphite">
                {' '}
                ({formatDuration(projection.data.horizon_months, language)})
              </span>
            )}{' '}
            · {t(`profile_${g.profile}` as StringKey)}
          </p>
        </div>
        <SketchButton sketchId="goal-tour" variant="quiet" onClick={replayTour}>
          {t('showMeAround')}
        </SketchButton>
      </header>

      <Panel title={t('projectionTitle')} anchor={projectionAnchor} id="goal-projection">
        {shown ? (
          <>
            <p>
              <span className="block text-graphite">
                {t('simChance', { target: formatMoney(shownTarget, language) })}
              </span>
              <Highlight redrawKey={`${chance}`}>
                <Figure kind="percent" value={chance} className="text-4xl font-bold" />
              </Highlight>
            </p>
            <ProjectionChart
              id={`goal-${goalId}-projection`}
              data={shown}
              targetCents={shownTarget}
              sketchy={!previewSimulation.isFetching}
              showContributions
              height={320}
              summary={projectionSummary}
            />
            <p className="sr-only">{projectionSummary}</p>
            {baseChance < SOLVE_AT && (
              <SolverPanel
                key={`${g.monthly_contribution_cents}-${g.target_date}-${g.target_cents}`}
                id="goal-solver"
                anchorId="goal-projection"
                solve={() => solveGoal(goalId)}
                onPreview={(option, solution) =>
                  setPreview(option && solution ? { option, solution } : null)
                }
                onApply={applyPlan}
                applying={updateGoal.isPending}
              />
            )}
          </>
        ) : (
          <Skeleton id="projection-loading" lines={4} />
        )}
      </Panel>

      <div className="grid gap-12 lg:grid-cols-12">
        <div className="flex flex-col gap-12 lg:col-span-5">
          <Panel title={t('balanceTitle')} anchor={balanceAnchor} id="goal-balance">
            {balance.data ? (
              <dl className="grid grid-cols-2 gap-x-6 gap-y-1">
                <dt className="text-sm text-graphite">{t('balanceTotal')}</dt>
                <dt className="text-sm text-graphite">{t('balanceContributed')}</dt>
                <dd className="m-0 text-2xl font-bold">
                  <Figure kind="money" value={total} decimals={2} />
                </dd>
                <dd className="m-0 text-2xl">
                  <Figure kind="money" value={balance.data.contributed_cents} decimals={2} />
                </dd>
                {balance.data.fees_cents > 0 && (
                  <>
                    <dt className="text-sm text-graphite">{t('balanceFees')}</dt>
                    <dd className="m-0">
                      <Figure kind="money" value={balance.data.fees_cents} decimals={2} />
                    </dd>
                  </>
                )}
              </dl>
            ) : (
              <Skeleton id="balance-loading" lines={2} />
            )}
            <h3 className="mt-2">{t('depositTitle')}</h3>
            <DepositForm goalId={goalId} />
          </Panel>

          <Panel title={t('allocationTitle')} id="goal-allocation">
            {total > 0 && balance.data ? (
              <AllocationBar id={`goal-${goalId}-actual`} weights={balance.data.weights} />
            ) : startingWeights ? (
              <>
                <p className="text-graphite">{t('allocationEmpty')}</p>
                <AllocationBar id={`goal-${goalId}-target`} weights={startingWeights} />
              </>
            ) : (
              <Skeleton id="allocation-loading" lines={2} />
            )}
          </Panel>
        </div>

        <div className="flex flex-col gap-12 lg:col-span-7">
          <Panel title={t('timeMachineTitle')} anchor={timeAnchor} id="goal-time">
            <p>{t('timeMachineIntro')}</p>
            {glidePath.data && projection.data ? (
              <TimeMachine
                goal={g}
                glidePath={glidePath.data}
                simulation={projection.data.simulation}
                anchorId="goal-time"
              />
            ) : (
              <Skeleton id="time-loading" lines={3} />
            )}
          </Panel>

          <Panel title={t('stressTitle')} anchor={stressAnchor} id="goal-stress">
            <p>{t('stressIntro')}</p>
            <StressTestPanel goalId={goalId} anchorId="goal-stress" />
          </Panel>
        </div>
      </div>

      <div className="grid gap-12 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <Panel title={t('ledgerTitle')} anchor={ledgerAnchor} id="goal-ledger">
            {entries.data && entries.data.length > 0 ? (
              <>
                <p className="text-sm text-graphite">{t('ledgerHint')}</p>
                <LedgerTable entries={entries.data} anchorId="goal-ledger" />
              </>
            ) : entries.data ? (
              <p>{t('ledgerEmpty')}</p>
            ) : (
              <Skeleton id="ledger-loading" lines={3} />
            )}
          </Panel>
        </div>
        <div className="lg:col-span-5">
          <Panel title={t('rebalancesTitle')} id="goal-rebalances">
            {rebalances.data ? (
              <RebalanceList entries={rebalances.data} anchorId="goal-rebalances" />
            ) : (
              <Skeleton id="rebalances-loading" lines={2} />
            )}
          </Panel>
        </div>
      </div>
    </div>
  )
}
