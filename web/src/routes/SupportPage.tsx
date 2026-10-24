import { useCallback, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Skeleton } from '../components/Skeleton'
import { SketchButton } from '../components/sketch/SketchButton'
import { ClientSearch } from '../features/support/ClientSearch'
import { ClientSummary } from '../features/support/ClientSummary'
import { explainEvent } from '../features/support/events'
import { QuestionPanel } from '../features/support/QuestionPanel'
import { Timeline } from '../features/support/Timeline'
import { useLanguage } from '../lib/i18n'
import { useReducedMotion } from '../lib/motion'
import {
  useSupportClient,
  useSupportTimeline,
  type SupportAnswer,
  type TimelineEvent,
} from '../lib/queries'
import { usePebble } from '../pebble/PebbleProvider'

const EVENT_ANCHOR = 'support-event'
const ANSWER_ANCHOR = 'support-answer'

/**
 * An internal page for a support agent: search a client, read their account as one timeline,
 * and ask plain-language questions that Pebble answers from that timeline.
 */
export function SupportPage() {
  const { t } = useLanguage()
  const pebble = usePebble()
  const [params, setParams] = useSearchParams()
  const clientId = Number(params.get('client')) || null
  const client = useSupportClient(clientId)
  const timeline = useSupportTimeline(clientId)
  const [highlight, setHighlight] = useState<{ clientId: number; ids: number[] } | null>(null)
  const panel = useRef<HTMLDivElement>(null)
  const reduced = useReducedMotion()

  // Highlights belong to the client they were asked about.
  const highlighted = useMemo(
    () => new Set(highlight && highlight.clientId === clientId ? highlight.ids : []),
    [highlight, clientId],
  )

  const selectClient = (id: number) => {
    setParams({ client: String(id) })
    pebble.dismiss()
  }

  const explain = useCallback(
    (event: TimelineEvent, element: HTMLElement) => {
      pebble.registerAnchor(EVENT_ANCHOR, element)
      pebble.say(explainEvent(event, EVENT_ANCHOR))
    },
    [pebble],
  )

  const showAnswer = (answer: SupportAnswer) => {
    if (clientId === null) return
    setHighlight({ clientId, ids: answer.event_ids })
    // The highlighted events come into view, and Pebble answers beside the question panel, so
    // its bubble never covers the events it talks about.
    const first = document.querySelector(`[data-event-id="${answer.event_ids[0]}"]`)
    first?.scrollIntoView?.({ block: 'center', behavior: reduced ? 'auto' : 'smooth' })
    pebble.registerAnchor(ANSWER_ANCHOR, panel.current)
    pebble.say({ title: answer.answer.title, text: answer.answer.body, anchorId: ANSWER_ANCHOR })
  }

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h1>{t('supportTitle')}</h1>
        <p className="mt-2 max-w-2xl">{t('supportIntro')}</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-12">
        <aside className="lg:col-span-3">
          <ClientSearch selectedId={clientId} onSelect={selectClient} />
        </aside>

        <div className="flex min-w-0 flex-col gap-6 lg:col-span-6">
          {clientId === null ? (
            <p className="text-lg">{t('supportEmpty')}</p>
          ) : client.isError || timeline.isError ? (
            <div role="alert" className="flex flex-col items-start gap-3">
              <p>{t('supportError')}</p>
              <SketchButton
                sketchId="support-retry"
                onClick={() => {
                  void client.refetch()
                  void timeline.refetch()
                }}
              >
                {t('tryAgain')}
              </SketchButton>
            </div>
          ) : !client.data || !timeline.data ? (
            <Skeleton id="support-loading" lines={8} />
          ) : (
            <>
              <ClientSummary client={client.data} />
              <div>
                <h2 className="text-2xl">{t('supportTimeline')}</h2>
                {timeline.data.length === 0 ? (
                  <p className="text-graphite">{t('supportTimelineEmpty')}</p>
                ) : (
                  <>
                    <p className="mb-3 text-sm text-graphite">
                      {t('supportTimelineSummary', { count: timeline.data.length })}
                    </p>
                    <Timeline events={timeline.data} highlighted={highlighted} onSelect={explain} />
                  </>
                )}
              </div>
            </>
          )}
        </div>

        <div className="lg:col-span-3">
          {clientId !== null && timeline.data && timeline.data.length > 0 && (
            <div ref={panel} className="lg:sticky lg:top-4">
              <QuestionPanel
                key={clientId}
                clientId={clientId}
                events={timeline.data}
                onAnswer={showAnswer}
              />
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
