import { useState } from 'react'
import { Skeleton } from '../components/Skeleton'
import { SketchButton } from '../components/sketch/SketchButton'
import { formatNumber, formatPercent } from '../lib/format'
import { useLanguage, type Language, type StringKey } from '../lib/i18n'
import { useObservability, type ObservabilityStats } from '../lib/queries'

const LOCALES: Record<Language, string> = { en: 'en-GB', fr: 'fr-FR' }
const SOURCES = ['ai', 'cache', 'fallback'] as const
const SOURCE_COLORS: Record<(typeof SOURCES)[number], string> = {
  ai: 'var(--chart-range)',
  cache: 'var(--leaf)',
  fallback: 'var(--graphite)',
}

function usd(value: number, language: Language): string {
  return new Intl.NumberFormat(LOCALES[language], {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: value < 1 ? 4 : 2,
  }).format(value)
}

function ms(value: number, language: Language): string {
  return `${formatNumber(Math.round(value), language)} ms`
}

function time(iso: string, language: Language): string {
  return new Intl.DateTimeFormat(LOCALES[language], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(iso))
}

function Tile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="border-l-4 border-ink/30 pl-3">
      <dt className="text-sm text-graphite">{label}</dt>
      <dd className="figure text-2xl font-bold">{value}</dd>
      {hint && <dd className="text-sm text-graphite">{hint}</dd>}
    </div>
  )
}

/** One bar split by where explanations came from, with an exact legend. */
function SourcesBar({ llm }: { llm: ObservabilityStats['llm'] }) {
  const { t, language } = useLanguage()
  const total = Math.max(llm.explanations, 1)
  return (
    <div>
      <h2 className="mb-2 text-2xl">{t('obsSources')}</h2>
      <div className="flex h-5 w-full gap-0.5 overflow-hidden rounded-sm bg-grid/40">
        {SOURCES.map((source) => {
          const count = llm.sources[source] ?? 0
          return count > 0 ? (
            <div
              key={source}
              style={{ width: `${(count / total) * 100}%`, background: SOURCE_COLORS[source] }}
            />
          ) : null
        })}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm">
        {SOURCES.map((source) => (
          <li key={source} className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="inline-block h-3 w-3 rounded-sm"
              style={{ background: SOURCE_COLORS[source] }}
            />
            {t(`obsSource_${source}` as StringKey)}:{' '}
            <span className="figure font-bold">{llm.sources[source] ?? 0}</span>
          </li>
        ))}
      </ul>
      {Object.keys(llm.fallback_reasons).length > 0 && (
        <p className="mt-1 text-sm text-graphite">
          {Object.entries(llm.fallback_reasons)
            .map(
              ([reason, count]) =>
                `${t(`obsReason_${reason}` as StringKey)} ${formatNumber(count, language)}`,
            )
            .join(' · ')}
        </p>
      )}
    </div>
  )
}

function Table({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[28rem] text-left text-sm">
        <thead>
          <tr className="font-hand text-base">
            {head.map((h, i) => (
              <th key={h} className={`py-1 pr-3 font-normal ${i > 0 ? 'text-right' : ''}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r} className="border-t border-dashed border-graphite/50">
              {row.map((cell, i) => (
                <td key={i} className={`py-1 pr-3 ${i > 0 ? 'figure text-right' : ''}`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Recent requests and log lines; selecting a request ID follows that one request. */
function Trail({ stats }: { stats: ObservabilityStats }) {
  const { t, language } = useLanguage()
  const [requestId, setRequestId] = useState<string | null>(null)
  const requests = stats.api.recent.filter((r) => !requestId || r.request_id === requestId)
  const logs = stats.logs.filter((l) => !requestId || l.request_id === requestId)
  const idButton = (id: string | null) =>
    id ? (
      <button
        type="button"
        onClick={() => setRequestId(id)}
        className="figure text-xs text-graphite underline decoration-dotted underline-offset-2"
        title={id}
      >
        {id.slice(0, 8)}
      </button>
    ) : null

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-2xl">{t('obsTrail')}</h2>
        {requestId ? (
          <p className="text-sm">
            {t('obsFilteredBy', { id: requestId.slice(0, 8) })} ·{' '}
            <button
              type="button"
              className="font-bold underline"
              onClick={() => setRequestId(null)}
            >
              {t('obsShowAll')}
            </button>
          </p>
        ) : (
          <p className="text-sm text-graphite">{t('obsTrailHint')}</p>
        )}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-1">{t('obsRecentRequests')}</h3>
          {requests.length === 0 ? (
            <p className="text-graphite">{t('obsNoRequests')}</p>
          ) : (
            <ul className="flex flex-col text-sm">
              {requests.map((r) => (
                <li
                  key={`${r.request_id}-${r.at}`}
                  className="flex flex-wrap items-baseline gap-x-3 border-t border-dashed border-graphite/40 py-1"
                >
                  <span className="figure text-graphite">{time(r.at, language)}</span>
                  <span
                    className={`figure font-bold ${r.status >= 500 ? 'text-red-pen' : r.status >= 400 ? 'text-graphite' : ''}`}
                  >
                    {r.status}
                  </span>
                  <span className="min-w-0 flex-1 truncate">
                    {r.method} {r.path}
                  </span>
                  <span className="figure text-graphite">{ms(r.duration_ms, language)}</span>
                  {idButton(r.request_id)}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="mb-1">{t('obsLogs')}</h3>
          <ul className="flex flex-col font-mono text-xs">
            {logs.map((line, i) => (
              <li
                key={`${line.at}-${i}`}
                className="flex flex-wrap items-baseline gap-x-2 border-t border-dashed border-graphite/40 py-1"
              >
                <span className="text-graphite">{time(line.at, language)}</span>
                <span
                  className={`font-bold ${line.level === 'warning' || line.level === 'error' ? 'text-red-pen' : ''}`}
                >
                  {line.level}
                </span>
                <span className="font-bold">{line.event}</span>
                <span className="min-w-0 flex-1 break-all text-graphite">
                  {Object.entries(line.fields)
                    .map(([k, v]) => `${k}=${String(v)}`)
                    .join(' ')}
                </span>
                {idButton(line.request_id)}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

/**
 * An internal page for the team: API traffic, how Pebble's explanations were produced and what
 * the AI cost, and a request-by-request trail, since the API last started.
 */
export function ObservabilityPage() {
  const { t, language } = useLanguage()
  const [autoRefresh, setAutoRefresh] = useState(true)
  const query = useObservability(autoRefresh)
  const stats = query.data

  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1>{t('obsTitle')}</h1>
          <p className="mt-2 max-w-2xl">{t('obsIntro')}</p>
          {stats && (
            <p className="mt-1 text-sm text-graphite">
              {t('obsSince', {
                date: new Intl.DateTimeFormat(LOCALES[language], {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                }).format(new Date(stats.since)),
              })}
            </p>
          )}
        </div>
        <label className="flex min-h-11 cursor-pointer items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="h-5 w-5 accent-[var(--ink)]"
          />
          {t('obsAutoRefresh')}
        </label>
      </div>

      {query.isError && !stats ? (
        <div role="alert" className="flex flex-col items-start gap-3">
          <p>{t('obsError')}</p>
          <SketchButton sketchId="obs-retry" onClick={() => query.refetch()}>
            {t('tryAgain')}
          </SketchButton>
        </div>
      ) : !stats ? (
        <Skeleton id="obs-loading" lines={6} />
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-5 md:grid-cols-4">
            <Tile label={t('obsRequests')} value={formatNumber(stats.api.requests, language)} />
            <Tile
              label={t('obsErrorRate')}
              value={formatPercent(stats.api.error_rate, language, 1)}
            />
            <Tile label={t('obsP95')} value={ms(stats.api.p95_ms, language)} />
            <Tile
              label={t('obsExplanations')}
              value={formatNumber(stats.llm.explanations, language)}
            />
            <Tile
              label={t('obsTokens')}
              value={`${formatNumber(stats.llm.input_tokens, language)} / ${formatNumber(stats.llm.output_tokens, language)}`}
            />
            <Tile
              label={t('obsCost')}
              value={stats.llm.cost_usd === null ? '—' : usd(stats.llm.cost_usd, language)}
              hint={
                stats.llm.cost_usd === null && stats.llm.calls > 0 ? t('obsCostUnknown') : undefined
              }
            />
            <Tile label={t('obsLatency')} value={ms(stats.llm.avg_latency_ms, language)} />
            <Tile
              label={t('obsCalls')}
              value={formatNumber(stats.llm.calls, language)}
              hint={
                stats.llm.enabled ? t('obsModel', { model: stats.llm.model }) : t('obsModelOff')
              }
            />
          </dl>

          <SourcesBar llm={stats.llm} />

          <div className="grid gap-8 lg:grid-cols-2">
            <section>
              <h2 className="mb-2 text-2xl">{t('obsRoutes')}</h2>
              <Table
                head={[t('obsRoute'), t('obsCount'), t('obsErrors'), t('obsMedian'), 'p95']}
                rows={stats.api.routes
                  .slice(0, 10)
                  .map((r) => [
                    `${r.method} ${r.route}`,
                    r.count,
                    r.errors,
                    ms(r.p50_ms, language),
                    ms(r.p95_ms, language),
                  ])}
              />
            </section>
            <section>
              <h2 className="mb-2 text-2xl">{t('obsTopics')}</h2>
              <Table
                head={[t('obsTopic'), t('obsExplanations'), t('obsCalls'), t('obsTokens'), '$']}
                rows={stats.llm.topics.map((topic) => [
                  topic.topic,
                  topic.explanations,
                  topic.calls,
                  `${formatNumber(topic.input_tokens, language)} / ${formatNumber(topic.output_tokens, language)}`,
                  topic.calls ? usd(topic.cost_usd, language) : '—',
                ])}
              />
            </section>
          </div>

          <section>
            <h2 className="mb-2 text-2xl">{t('obsRecentCalls')}</h2>
            {stats.llm.recent.length === 0 ? (
              <p className="text-graphite">{t('obsNoCalls')}</p>
            ) : (
              <Table
                head={[t('obsTopic'), t('obsTokens'), 'ms', '$', '']}
                rows={stats.llm.recent.map((call) => [
                  `${time(call.at, language)} · ${call.topic}`,
                  `${formatNumber(call.input_tokens, language)} / ${formatNumber(call.output_tokens, language)}`,
                  formatNumber(Math.round(call.latency_ms), language),
                  call.cost_usd === null ? '—' : usd(call.cost_usd, language),
                  call.ok ? '✓' : (call.error ?? '✗'),
                ])}
              />
            )}
          </section>

          <Trail stats={stats} />
        </>
      )}
    </section>
  )
}
