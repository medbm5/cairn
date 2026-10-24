import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLanguage } from '../lib/i18n'
import { useCreateGoal, type Profile } from '../lib/queries'
import { usePebble } from '../pebble/PebbleProvider'
import { GoalStep } from '../features/onboarding/GoalStep'
import { parseEuros, targetDate, type GoalForm } from '../features/onboarding/goalForm'
import { ProfileReveal } from '../features/onboarding/ProfileReveal'
import { QuestionsStep } from '../features/onboarding/QuestionsStep'

type Step = 'goal' | 'questions' | 'profile'
const STEPS: Step[] = ['goal', 'questions', 'profile']

export function StartPage() {
  const { t } = useLanguage()
  const navigate = useNavigate()
  const pebble = usePebble()
  const createGoal = useCreateGoal()
  const [step, setStep] = useState<Step>('goal')
  const [form, setForm] = useState<GoalForm>({
    type: null,
    name: '',
    target: '',
    date: '',
    monthly: '',
  })
  const [answers, setAnswers] = useState<Record<string, string>>({})

  const stepTitle = {
    goal: t('startStepGoal'),
    questions: t('startStepQuestions'),
    profile: t('startStepProfile'),
  }[step]

  const confirm = (profile: Profile) => {
    createGoal.mutate(
      {
        name: form.name.trim(),
        type: form.type ?? 'other',
        target_cents: parseEuros(form.target) ?? 0,
        target_date: targetDate(form.date, new Date()),
        monthly_contribution_cents: parseEuros(form.monthly) ?? 0,
        profile: profile.key,
      },
      {
        onSuccess: (goal) => {
          pebble.dismiss()
          navigate(`/goals/${goal.id}`)
        },
      },
    )
  }

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1>{t('startTitle')}</h1>
        <p className="mt-2 text-graphite">
          {t('stepCounter', { step: STEPS.indexOf(step) + 1, total: STEPS.length })}:{' '}
          <span className="font-bold text-ink">{stepTitle}</span>
        </p>
      </div>
      {step === 'goal' && (
        <GoalStep form={form} onChange={setForm} onDone={() => setStep('questions')} />
      )}
      {step === 'questions' && (
        <QuestionsStep
          answers={answers}
          onAnswer={(question, option) => setAnswers((a) => ({ ...a, [question]: option }))}
          onBack={() => setStep('goal')}
          onDone={() => setStep('profile')}
        />
      )}
      {step === 'profile' && (
        <ProfileReveal
          answers={answers}
          creating={createGoal.isPending}
          createError={createGoal.error?.message ?? null}
          onConfirm={confirm}
          onBack={() => setStep('questions')}
        />
      )}
    </section>
  )
}
