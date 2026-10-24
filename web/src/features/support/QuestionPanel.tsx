import { useState, type FormEvent } from 'react'
import { Figure } from '../../components/Figure'
import { SketchButton } from '../../components/sketch/SketchButton'
import { useLanguage } from '../../lib/i18n'
import { useAskSupport, type SupportAnswer, type TimelineEvent } from '../../lib/queries'
import { monthLabel, worstMonth } from './events'

/**
 * Suggested and free-text questions about the client. The answer comes from the timeline only;
 * its breakdown is shown here in exact figures, and the page hands the answer to Pebble.
 */
export function QuestionPanel({
  clientId,
  events,
  onAnswer,
}: {
  clientId: number
  events: TimelineEvent[]
  onAnswer: (answer: SupportAnswer) => void
}) {
  const { t, language } = useLanguage()
  const ask = useAskSupport(clientId)
  const [question, setQuestion] = useState('')
  const answer = ask.data

  // Suggest the month that actually fell, so the first question is always a useful one.
  const fallMonth = worstMonth(events)
  const suggestions: { text: string; month?: string }[] = [
    ...(fallMonth
      ? [
          {
            text: t('supportAskWhyDown', { month: monthLabel(fallMonth, language).split(' ')[0] }),
            month: fallMonth,
          },
        ]
      : []),
    { text: t('supportAskLastRebalance') },
  ]

  const send = (text: string, month?: string) => {
    if (!text.trim()) return
    ask.mutate({ question: text.trim(), month, language }, { onSuccess: onAnswer })
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    send(question)
  }

  const b = answer?.focus === 'month_change' ? answer.breakdown : null
  const rows: [string, number, boolean][] = b
    ? [
        [t('supportStart'), b.start_balance_cents, false],
        [t('supportMarket'), b.market_effect_cents, true],
        [t('supportDeposits'), b.deposits_cents, true],
        [t('supportFeesTaken'), -b.fees_cents, true],
        [t('supportEnd'), b.end_balance_cents, false],
      ]
    : []

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-2xl">{t('supportQuestions')}</h2>
      <div>
        <p className="mb-2 text-sm text-graphite">{t('supportSuggested')}</p>
        <ul className="flex flex-col gap-2">
          {suggestions.map(({ text, month }) => (
            <li key={text}>
              <button
                type="button"
                onClick={() => send(text, month)}
                disabled={ask.isPending}
                className="min-h-11 border-2 border-dashed border-graphite/70 px-3 py-1.5 text-left hover:border-solid hover:border-ink disabled:opacity-50"
              >
                {text}
              </button>
            </li>
          ))}
        </ul>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-2">
        <label htmlFor="support-question" className="font-bold">
          {t('supportQuestionLabel')}
        </label>
        <textarea
          id="support-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={300}
          rows={3}
          className="border-2 border-dashed border-graphite bg-transparent p-2 text-ink focus:border-solid focus:border-ink"
        />
        <div>
          <SketchButton
            sketchId="support-ask"
            variant="primary"
            type="submit"
            disabled={ask.isPending || !question.trim()}
          >
            {t('supportAsk')}
          </SketchButton>
        </div>
      </form>
      <div aria-live="polite">
        {ask.isPending && <p className="font-hand">{t('supportAsking')}</p>}
        {ask.isError && <p role="alert">{t('supportAskError')}</p>}
        {answer && !ask.isPending && (
          <div className="flex flex-col gap-2">
            <p className="font-bold">{answer.answer.title}</p>
            <p>{answer.answer.body}</p>
            {b && (
              <table className="w-full text-left">
                <caption className="mb-1 text-left text-sm text-graphite">
                  {t('supportBreakdown', { month: monthLabel(b.month, language) })}
                </caption>
                <tbody>
                  {rows.map(([label, cents, part]) => (
                    <tr
                      key={label}
                      className={part ? '' : 'border-t border-dashed border-graphite/60'}
                    >
                      <th scope="row" className={`py-0.5 font-normal ${part ? 'pl-3' : ''}`}>
                        {label}
                      </th>
                      <td className="py-0.5 text-right">
                        <Figure
                          kind="money"
                          value={cents}
                          decimals={2}
                          className={cents < 0 ? 'text-red-pen' : part ? '' : 'font-bold'}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {answer.event_ids.length > 0 && (
              <p className="text-sm text-graphite">
                {t('supportHighlighted', { count: answer.event_ids.length })}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
