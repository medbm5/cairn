import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { Figure } from '../../components/Figure'
import { PaperCard } from '../../components/sketch/PaperCard'
import { SketchButton } from '../../components/sketch/SketchButton'
import { formatDate, formatDuration, formatMoney, formatPercent } from '../../lib/format'
import { useLanguage, type StringKey } from '../../lib/i18n'
import type { Solution, SolverOption } from '../../lib/queries'
import { usePebble } from '../../pebble/PebbleProvider'
import { solverFacts } from './facts'

/**
 * "How do I get there?": the goal solver's three options as hand-drawn note cards. Hovering or
 * focusing a card previews it on the chart (through `onPreview`); "Use this plan" applies it.
 */
export function SolverPanel({
  id,
  anchorId,
  solve,
  onPreview,
  onApply,
  applying = false,
}: {
  id: string
  /** The chart Pebble walks to while the options are open. */
  anchorId: string
  solve: () => Promise<Solution>
  /** Called with the option to preview (and the answer it belongs to), or null to stop. */
  onPreview: (option: SolverOption | null, solution?: Solution) => void
  onApply: (option: SolverOption) => void
  applying?: boolean
}) {
  const { t, language } = useLanguage()
  const pebble = usePebble()
  const solver = useMutation({ mutationFn: solve })
  const solution = solver.data
  const pointing = useRef(false)
  const { pointAt } = pebble
  useEffect(
    () => () => {
      if (pointing.current) pointAt(null)
    },
    [pointAt],
  )

  const open = () => {
    pointing.current = true
    pebble.pointAt(anchorId)
    solver.mutate()
  }
  const close = () => {
    onPreview(null)
    pointing.current = false
    pebble.pointAt(null)
    solver.reset()
  }
  const explain = () => {
    if (solution) pebble.say({ topic: 'solver', facts: solverFacts(solution), anchorId })
  }

  const money = (cents: number) => formatMoney(cents, language)
  const label = (option: SolverOption): string => {
    if (!option.feasible) return t(`solverOutOfReach_${option.lever}` as StringKey)
    if (option.lever === 'contribution') return t('solverSave', { amount: money(option.value) })
    if (option.lever === 'horizon')
      return t('solverPushDate', { date: formatDate(option.target_date!, language) })
    return t('solverAimFor', { amount: money(option.value) })
  }
  const change = (option: SolverOption): string => {
    const size = Math.abs(option.delta)
    if (option.delta === 0) return t('solverNoChange')
    if (option.lever === 'contribution')
      return t(option.delta > 0 ? 'solverMoreMonthly' : 'solverLessMonthly', {
        amount: money(size),
      })
    if (option.lever === 'horizon')
      return t(option.delta > 0 ? 'solverLater' : 'solverSooner', {
        duration: formatDuration(size, language),
      })
    return t(option.delta > 0 ? 'solverMoreTarget' : 'solverLessTarget', { amount: money(size) })
  }

  if (!solution) {
    return (
      <div className="flex flex-col items-start gap-2">
        <SketchButton
          sketchId={`${id}-open`}
          variant="primary"
          onClick={open}
          disabled={solver.isPending}
          aria-expanded={false}
        >
          {solver.isPending ? t('solverWorking') : t('solverOpen')}
        </SketchButton>
        {solver.isError && (
          <p role="alert" className="text-red-pen">
            {t('solverError')}
          </p>
        )}
      </div>
    )
  }

  const aim = formatPercent(solution.target_probability, language)
  // Read aloud when the cards appear: the same options, as one sentence.
  const spoken = solution.options.map(
    (o) =>
      `${label(o)}: ${t('solverChance', { chance: formatPercent(o.success_probability, language) })}`,
  )

  return (
    <section aria-labelledby={`${id}-title`} className="flex flex-col gap-4">
      <div>
        <h3 id={`${id}-title`} className="font-hand text-2xl">
          {t('solverTitle', { aim })}
        </h3>
        <p className="text-graphite">{t('solverIntro')}</p>
      </div>
      <p className="sr-only" aria-live="polite">
        {t('solverSpoken', { aim, options: spoken.join('; ') })}
      </p>
      <ul className="grid gap-6 sm:grid-cols-3">
        {solution.options.map((option, index) => (
          <li
            key={option.lever}
            className="note-in"
            style={{ animationDelay: `${index * 140}ms` }}
            onMouseEnter={() => option.feasible && onPreview(option, solution)}
            onMouseLeave={() => onPreview(null)}
            onFocus={() => option.feasible && onPreview(option, solution)}
            onBlur={() => onPreview(null)}
          >
            <PaperCard id={`${id}-${option.lever}`} className="h-full">
              <div className={`flex h-full flex-col gap-2 ${option.feasible ? '' : 'opacity-70'}`}>
                <p className="font-hand text-xl leading-snug">{label(option)}</p>
                {option.feasible && (
                  <>
                    <p>
                      <Figure
                        kind="percent"
                        value={option.success_probability}
                        className="text-2xl font-bold"
                      />{' '}
                      <span className="text-graphite">{t('solverChanceSuffix')}</span>
                    </p>
                    <p className="text-sm text-graphite">{change(option)}</p>
                    <SketchButton
                      sketchId={`${id}-${option.lever}-use`}
                      variant="secondary"
                      className="mt-auto self-start"
                      onClick={() => onApply(option)}
                      disabled={applying}
                      aria-label={`${t('solverUse')}: ${label(option)}`}
                    >
                      {t('solverUse')}
                    </SketchButton>
                  </>
                )}
              </div>
            </PaperCard>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-3">
        <SketchButton sketchId={`${id}-explain`} variant="quiet" onClick={explain}>
          {t('solverExplain')}
        </SketchButton>
        <SketchButton sketchId={`${id}-close`} variant="quiet" onClick={close}>
          {t('solverClose')}
        </SketchButton>
      </div>
    </section>
  )
}
