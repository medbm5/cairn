import { Link } from 'react-router-dom'
import { Figure } from '../../components/Figure'
import { PaperCard } from '../../components/sketch/PaperCard'
import { formatDate, formatMoney } from '../../lib/format'
import { useLanguage } from '../../lib/i18n'
import { useBalance, useProjection, type Goal } from '../../lib/queries'
import { nextMilestone } from './ledger'
import { ProgressRing } from './ProgressRing'

/** A goal on the dashboard: a taped paper card with its progress ring and next milestone. */
export function GoalCard({ goal }: { goal: Goal }) {
  const { t, language } = useLanguage()
  const balance = useBalance(goal.id)
  const projection = useProjection(goal.id)
  const value = balance.data?.total_cents ?? 0
  const p50 = projection.data?.simulation.p50
  const milestone = nextMilestone(value, goal.target_cents)

  return (
    <PaperCard id={`goal-card-${goal.id}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-2xl">
            <Link
              to={`/goals/${goal.id}`}
              className="no-underline after:absolute after:inset-0"
              aria-label={t('openGoal', { name: goal.name })}
            >
              {goal.name}
            </Link>
          </h2>
          <p className="text-graphite">
            <Figure kind="money" value={goal.target_cents} />{' '}
            {t('goalBy', { date: formatDate(goal.target_date, language) })}
          </p>
        </div>
        <ProgressRing id={`ring-${goal.id}`} share={value / goal.target_cents} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1">
        <dt className="text-sm text-graphite">{t('currentValue')}</dt>
        <dt className="text-sm text-graphite">{t('medianAtGoal')}</dt>
        <dd className="m-0 text-lg font-bold">
          <Figure kind="money" value={value} />
        </dd>
        <dd className="m-0 text-lg font-bold">
          {p50 ? <Figure kind="money" value={p50[p50.length - 1]} /> : '…'}
        </dd>
      </dl>
      <p className="mt-3 text-sm">
        {milestone === null
          ? t('goalReached')
          : t('nextMilestone', { amount: formatMoney(milestone, language) })}
      </p>
    </PaperCard>
  )
}
