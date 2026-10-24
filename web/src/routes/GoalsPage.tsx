import { Skeleton } from '../components/Skeleton'
import { SketchButton, SketchLink } from '../components/sketch/SketchButton'
import { GoalCard } from '../features/goals/GoalCard'
import { useLanguage } from '../lib/i18n'
import { useGoals } from '../lib/queries'

export function GoalsPage() {
  const { t } = useLanguage()
  const goals = useGoals()

  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1>{t('goalsTitle')}</h1>
        <SketchLink sketchId="goals-new" to="/start" variant="primary">
          {t('newGoal')}
        </SketchLink>
      </div>
      {goals.isPending ? (
        <Skeleton id="goals-loading" lines={4} />
      ) : goals.isError ? (
        <div role="alert" className="flex flex-col items-start gap-3">
          <p>{t('goalsError')}</p>
          <SketchButton sketchId="goals-retry" onClick={() => goals.refetch()}>
            {t('tryAgain')}
          </SketchButton>
        </div>
      ) : goals.data.length === 0 ? (
        <p className="max-w-lg text-lg">{t('goalsEmpty')}</p>
      ) : (
        <ul className="grid gap-10 md:grid-cols-2 xl:grid-cols-3">
          {goals.data.map((goal) => (
            <li key={goal.id} className="relative">
              <GoalCard goal={goal} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
