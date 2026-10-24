import { formatDate, formatMoney } from '../../lib/format'
import { useLanguage } from '../../lib/i18n'
import type { JournalEntry } from '../../lib/queries'
import { usePebble } from '../../pebble/PebbleProvider'
import { entryAmount } from './ledger'

const DRIFT_THRESHOLD = 0.05

export function RebalanceList({
  entries,
  anchorId,
}: {
  entries: JournalEntry[]
  anchorId: string
}) {
  const { t, language } = useLanguage()
  const pebble = usePebble()
  if (entries.length === 0) return <p className="text-graphite">{t('rebalancesEmpty')}</p>
  return (
    <ul className="flex flex-col gap-1">
      {entries.map((entry) => (
        <li key={entry.id}>
          <button
            type="button"
            className="min-h-9 text-left underline decoration-dotted decoration-2 underline-offset-4"
            onClick={() =>
              pebble.say({
                topic: 'rebalance',
                anchorId,
                facts: { threshold: DRIFT_THRESHOLD, moved_cents: entryAmount(entry) },
              })
            }
          >
            <span className="figure">{formatDate(entry.created_at, language)}</span>:{' '}
            {t('rebalanceMoved', { amount: formatMoney(entryAmount(entry), language) })}
          </button>
        </li>
      ))}
    </ul>
  )
}
