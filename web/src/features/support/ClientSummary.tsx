import { Figure } from '../../components/Figure'
import { formatDate, formatMoney } from '../../lib/format'
import { useLanguage, type StringKey } from '../../lib/i18n'
import type { SupportClient } from '../../lib/queries'

/** Who the client is and where their account stands, in exact figures. */
export function ClientSummary({ client }: { client: SupportClient }) {
  const { t, language } = useLanguage()
  const stats: [string, number][] = [
    [t('supportBalance'), client.total_balance_cents],
    [t('supportContributed'), client.total_contributed_cents],
    [t('supportFees'), client.total_fees_cents],
  ]
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2>{client.name}</h2>
        {client.email && <p className="text-graphite">{client.email}</p>}
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
        {stats.map(([label, cents]) => (
          <div key={label}>
            <dt className="text-sm text-graphite">{label}</dt>
            <dd className="text-xl font-bold">
              <Figure kind="money" value={cents} decimals={2} />
            </dd>
          </div>
        ))}
        <div>
          <dt className="text-sm text-graphite">{t('supportProfile')}</dt>
          <dd className="font-bold">
            {client.profile ? t(`profile_${client.profile}` as StringKey) : '—'}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-graphite">{t('supportLastActivity')}</dt>
          <dd className="figure font-bold">
            {client.last_activity
              ? formatDate(client.last_activity, language)
              : t('supportNoActivity')}
          </dd>
        </div>
      </dl>
      {client.goals.length > 0 && (
        <div>
          <h3 className="mb-1">{t('supportGoals')}</h3>
          <ul className="flex flex-col gap-1">
            {client.goals.map((goal) => (
              <li
                key={goal.id}
                className="flex flex-wrap items-baseline justify-between gap-x-4 border-t border-dashed border-graphite/60 py-1"
              >
                <span>
                  {goal.name}{' '}
                  <span className="text-sm text-graphite">
                    · {t(`profile_${goal.profile}` as StringKey)} ·{' '}
                    {formatMoney(goal.target_cents, language)} ·{' '}
                    {formatDate(goal.target_date, language)}
                  </span>
                </span>
                <Figure
                  kind="money"
                  value={goal.balance_cents}
                  decimals={2}
                  className="font-bold"
                />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
