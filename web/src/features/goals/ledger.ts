import type { JournalEntry } from '../../lib/queries'

const line = (entry: JournalEntry, account: string) =>
  entry.lines.find((l) => l.account === account)?.amount_cents ?? 0

/**
 * The amount a person would name for an entry, in cents: money in for a deposit, the fee,
 * the total moved in a rebalance, the gain (or loss, negative) of a market movement.
 */
export function entryAmount(entry: JournalEntry): number {
  switch (entry.kind) {
    case 'deposit':
      return -line(entry, 'external_bank')
    case 'fee':
      return line(entry, 'fees')
    case 'market':
      return -line(entry, 'market')
    default:
      return entry.lines.filter((l) => l.amount_cents > 0).reduce((s, l) => s + l.amount_cents, 0)
  }
}

/** The next quarter of the target not yet reached, or null once the target is reached. */
export function nextMilestone(valueCents: number, targetCents: number): number | null {
  if (valueCents >= targetCents) return null
  const quarter = targetCents / 4
  return Math.round((Math.floor(valueCents / quarter) + 1) * quarter)
}

/** A fresh idempotency key for one deposit submission. */
export function newIdempotencyKey(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
}
