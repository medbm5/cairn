import { useRef, useState, type FormEvent } from 'react'
import { Field } from '../../components/Field'
import { MonthPicker } from '../../components/MonthPicker'
import { SketchButton } from '../../components/sketch/SketchButton'
import { SketchBox } from '../../components/sketch/SketchBox'
import { useLanguage, type StringKey } from '../../lib/i18n'
import { PebbleInline } from '../../pebble/PebbleInline'
import { usePebble, usePebbleAnchor } from '../../pebble/PebbleProvider'
import { validateGoal, type GoalErrors, type GoalForm } from './goalForm'
import { GoalTypeIcon } from './GoalTypeIcon'
import { GOAL_TYPES } from './goalTypes'

/** The month `months` from now, as YYYY-MM. */
function monthsFromNow(months: number): string {
  const today = new Date()
  const date = new Date(today.getFullYear(), today.getMonth() + months, 1)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

export function GoalStep({
  form,
  onChange,
  onDone,
}: {
  form: GoalForm
  onChange: (form: GoalForm) => void
  onDone: () => void
}) {
  const { t } = useLanguage()
  const pebble = usePebble()
  const dateAnchor = usePebbleAnchor('goal-date')
  const [errors, setErrors] = useState<GoalErrors>({})
  const explainedDate = useRef(false)

  const explainDate = () => pebble.say({ term: 'time_horizon', anchorId: 'goal-date' })
  const set = <K extends keyof GoalForm>(key: K, value: GoalForm[K]) =>
    onChange({ ...form, [key]: value })
  const error = (key: keyof GoalForm) => (errors[key] ? t(errors[key] as StringKey) : undefined)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const found = validateGoal(form, new Date())
    setErrors(found)
    if (Object.keys(found).length === 0) onDone()
  }

  return (
    <form onSubmit={submit} noValidate className="flex max-w-2xl flex-col gap-6">
      <fieldset>
        <legend className="mb-3 font-hand text-2xl">{t('goalTypeQuestion')}</legend>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {GOAL_TYPES.map((type) => {
            const selected = form.type === type
            return (
              <label key={type} className="sketch-focus cursor-pointer">
                <input
                  type="radio"
                  name="goal-type"
                  value={type}
                  checked={selected}
                  onChange={() => set('type', type)}
                  className="sr-only"
                />
                <SketchBox
                  id={`goal-type-${type}`}
                  className={`flex flex-col items-center gap-1 p-3 text-center ${
                    selected ? 'bg-highlighter/40 font-bold' : ''
                  }`}
                  options={selected ? { strokeWidth: 2.6 } : undefined}
                >
                  <GoalTypeIcon type={type} className="mx-auto h-12 w-12 text-ink" />
                  <span className="text-sm">{t(`goalType_${type}` as StringKey)}</span>
                </SketchBox>
              </label>
            )
          })}
        </div>
        {errors.type && (
          <p role="alert" className="mt-2 text-sm font-bold text-red-pen">
            {t(errors.type)}
          </p>
        )}
      </fieldset>

      <Field
        label={t('goalNameLabel')}
        placeholder={t('goalNamePlaceholder')}
        value={form.name}
        maxLength={100}
        onChange={(e) => set('name', e.target.value)}
        error={error('name')}
      />
      <Field
        label={t('targetLabel')}
        inputMode="decimal"
        value={form.target}
        onChange={(e) => set('target', e.target.value)}
        error={error('target')}
      />
      <div ref={dateAnchor}>
        <MonthPicker
          label={t('dateLabel')}
          hint={t('dateHint')}
          value={form.date}
          onChange={(date) => set('date', date)}
          min={monthsFromNow(12)}
          max={monthsFromNow(480)}
          onFocus={() => {
            if (explainedDate.current) return
            explainedDate.current = true
            explainDate()
          }}
          error={error('date')}
        />
        <button type="button" onClick={explainDate} className="mt-1 min-h-11 text-sm underline">
          {t('whyDate')}
        </button>
        <PebbleInline anchorId="goal-date" />
      </div>
      <Field
        label={t('monthlyLabel')}
        inputMode="decimal"
        value={form.monthly}
        onChange={(e) => set('monthly', e.target.value)}
        error={error('monthly')}
      />
      <div>
        <SketchButton sketchId="goal-continue" type="submit" variant="primary">
          {t('continue')}
        </SketchButton>
      </div>
    </form>
  )
}
