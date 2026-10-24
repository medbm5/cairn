import { useState } from 'react'
import { Field } from '../../components/Field'
import { useLanguage } from '../../lib/i18n'
import { useSupportClients } from '../../lib/queries'
import { useDebounced } from '../../lib/useSettled'

/** Search clients by name or email; the list pages through results. */
export function ClientSearch({
  selectedId,
  onSelect,
}: {
  selectedId: number | null
  onSelect: (clientId: number) => void
}) {
  const { t } = useLanguage()
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const debounced = useDebounced(query, 250)
  const clients = useSupportClients(debounced, page)
  const data = clients.data
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  return (
    <div className="flex flex-col gap-4">
      <Field
        label={t('supportSearchLabel')}
        hint={t('supportSearchHint')}
        type="search"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setPage(1)
        }}
        autoComplete="off"
      />
      {clients.isError && <p role="alert">{t('supportError')}</p>}
      {data && (
        <>
          <p className="text-sm text-graphite" aria-live="polite">
            {data.total === 0 ? t('supportNoResults') : t('supportResults', { count: data.total })}
          </p>
          <ul className="flex flex-col gap-1">
            {data.items.map((client) => (
              <li key={client.id}>
                <button
                  type="button"
                  onClick={() => onSelect(client.id)}
                  aria-current={client.id === selectedId ? 'true' : undefined}
                  className={`flex min-h-11 w-full flex-col items-start border-l-4 px-3 py-1.5 text-left ${
                    client.id === selectedId
                      ? 'border-highlighter bg-highlighter/20 font-bold'
                      : 'border-transparent'
                  }`}
                >
                  <span>{client.name}</span>
                  <span className="text-sm font-normal text-graphite">
                    {client.email ?? '—'} · {t('supportGoalCount', { count: client.goal_count })}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {pages > 1 && (
            <div className="flex items-center justify-between gap-2 text-sm">
              <button
                type="button"
                className="min-h-11 px-2 font-bold underline disabled:opacity-40"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                {t('supportPrevious')}
              </button>
              <span className="figure text-graphite">
                {page} / {pages}
              </span>
              <button
                type="button"
                className="min-h-11 px-2 font-bold underline disabled:opacity-40"
                disabled={page >= pages}
                onClick={() => setPage(page + 1)}
              >
                {t('supportNext')}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
