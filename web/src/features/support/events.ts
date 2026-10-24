import type { Language } from '../../lib/i18n'
import type { TimelineEvent } from '../../lib/queries'
import type { SayRequest } from '../../pebble/PebbleProvider'

const LOCALES: Record<Language, string> = { en: 'en-GB', fr: 'fr-FR' }
const DRIFT_THRESHOLD = 0.05

/** "2026-03" for an event dated in March 2026. */
export function monthKey(event: TimelineEvent): string {
  return event.date.slice(0, 7)
}

/** "March 2026" / "mars 2026". */
export function monthLabel(key: string, language: Language): string {
  const [year, month] = key.split('-').map(Number)
  return new Intl.DateTimeFormat(LOCALES[language], {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(Date.UTC(year, month - 1, 1)))
}

/** "28 Mar" / "28 mars". */
export function dayLabel(event: TimelineEvent, language: Language): string {
  return new Intl.DateTimeFormat(LOCALES[language], {
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  }).format(new Date(event.date))
}

/** Events grouped by month, keeping their order. */
export function groupByMonth(events: TimelineEvent[]): [string, TimelineEvent[]][] {
  const groups = new Map<string, TimelineEvent[]>()
  for (const event of events) {
    const key = monthKey(event)
    groups.set(key, [...(groups.get(key) ?? []), event])
  }
  return [...groups]
}

/** The month whose value fell the most (rebalances move money but change nothing), if any. */
export function worstMonth(events: TimelineEvent[]): string | null {
  const changes = new Map<string, number>()
  for (const event of events) {
    if (event.type === 'rebalance') continue
    changes.set(monthKey(event), (changes.get(monthKey(event)) ?? 0) + event.amount_cents)
  }
  let worst: [string, number] | null = null
  for (const entry of changes) if (worst === null || entry[1] < worst[1]) worst = entry
  return worst && worst[1] < 0 ? worst[0] : null
}

/** What Pebble is asked when a timeline event is selected. */
export function explainEvent(event: TimelineEvent, anchorId: string): SayRequest {
  const changes = (event.payload.by_asset ?? event.payload.transfers ?? {}) as Record<
    string,
    number
  >
  const holdings = Object.keys(changes).map((asset) => `holding:${asset}`)
  if (event.type === 'rebalance') {
    return {
      topic: 'rebalance',
      anchorId,
      facts: { threshold: DRIFT_THRESHOLD, moved_cents: event.amount_cents },
    }
  }
  const counterpart: Record<string, string> = {
    deposit: 'external_bank',
    fee: 'fees',
    market: 'market',
  }
  return {
    topic: 'ledger_entry',
    anchorId,
    facts: {
      kind: event.type,
      amount_cents: Math.abs(event.amount_cents),
      accounts: [counterpart[event.type] ?? event.type, ...holdings],
    },
  }
}
