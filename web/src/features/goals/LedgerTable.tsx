import { Figure } from '../../components/Figure'
import { useLanguage, type StringKey } from '../../lib/i18n'
import type { JournalEntry } from '../../lib/queries'
import { usePebble } from '../../pebble/PebbleProvider'
import { entryAmount } from './ledger'

const DATE = { day: 'numeric', month: 'short', year: 'numeric' } as const

/** The ledger as a handwritten-style table with crisp figures. Each line can be explained. */
export function LedgerTable({ entries, anchorId }: { entries: JournalEntry[]; anchorId: string }) {
  const { t, language } = useLanguage()
  const pebble = usePebble()
  const explain = (entry: JournalEntry) =>
    pebble.say({
      topic: 'ledger_entry',
      anchorId,
      facts: {
        kind: entry.kind,
        amount_cents: Math.abs(entryAmount(entry)),
        accounts: entry.lines.map((l) => l.account),
      },
    })

  return (
    <table className="w-full border-collapse text-left">
      <thead>
        <tr className="font-hand text-lg">
          <th className="py-2 pr-3 font-normal">{t('ledgerDate')}</th>
          <th className="py-2 pr-3 font-normal">{t('ledgerWhat')}</th>
          <th className="py-2 text-right font-normal">{t('ledgerAmount')}</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => {
          const amount = entryAmount(entry)
          return (
            <tr key={entry.id} className="border-t border-dashed border-graphite/60">
              <td className="py-1.5 pr-3 text-sm text-graphite">
                {new Intl.DateTimeFormat(language === 'fr' ? 'fr-FR' : 'en-GB', DATE).format(
                  new Date(entry.created_at),
                )}
              </td>
              <td className="py-1.5 pr-3">
                <button
                  type="button"
                  onClick={() => explain(entry)}
                  className="min-h-9 text-left underline decoration-dotted decoration-2 underline-offset-4"
                >
                  {t(`entry_${entry.kind}` as StringKey)}
                </button>
              </td>
              <td className="py-1.5 text-right">
                <Figure
                  kind="money"
                  value={amount}
                  decimals={2}
                  className={amount < 0 ? 'text-red-pen' : ''}
                />
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
