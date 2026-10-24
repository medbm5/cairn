import { useMemo, type ReactNode } from 'react'
import { Figure } from '../../components/Figure'
import { PaperCard } from '../../components/sketch/PaperCard'
import { RoughPaths } from '../../components/sketch/RoughPaths'
import { formatDate, formatMoney, formatPercent } from '../../lib/format'
import { useLanguage } from '../../lib/i18n'
import { PEN, seedFrom, sketch } from '../../lib/rough'
import { useDrawOn } from '../../lib/useDrawOn'
import { useInView } from '../../lib/useInView'
import { Term } from '../../pebble/Term'
import example from './example.json'

const ASSET_LABELS: Record<string, { en: string; fr: string }> = {
  external_bank: { en: 'From your bank', fr: 'Depuis votre banque' },
  'holding:global_equity': { en: 'Global shares', fr: 'Actions mondiales' },
  'holding:emerging_equity': { en: 'Emerging-market shares', fr: 'Actions émergentes' },
  'holding:euro_gov_bonds': { en: 'Euro government bonds', fr: "Obligations d'État euro" },
  'holding:money_market': { en: 'Money market', fr: 'Monétaire' },
}

function Section({
  title,
  body,
  children,
}: {
  title: string
  body: ReactNode
  children: ReactNode
}) {
  return (
    <section className="grid gap-8 py-14 lg:grid-cols-12 lg:items-center">
      <div className="lg:col-span-5">
        <h2>{title}</h2>
        <p className="mt-3 max-w-md text-lg">{body}</p>
      </div>
      <div className="lg:col-span-7">{children}</div>
    </section>
  )
}

export function GoalSection() {
  const { t, language } = useLanguage()
  const date = new Date()
  date.setMonth(date.getMonth() + example.horizon_months)
  const stop = example.stops.find((s) => s.monthly_contribution_cents === 400_00)!
  return (
    <Section title={t('sectionGoalTitle')} body={t('sectionGoalBody')}>
      <PaperCard id="landing-goal" className="max-w-sm">
        <p className="font-hand text-2xl">{t('exampleGoalName')}</p>
        <p className="mt-2 text-3xl font-bold">
          <Figure kind="money" value={example.target_cents} />
        </p>
        <p className="text-graphite">
          {t('goalBy', { date: formatDate(date.toISOString(), language) })}
        </p>
        <p className="mt-2">
          {t('perMonth', { amount: formatMoney(stop.monthly_contribution_cents, language) })}
        </p>
      </PaperCard>
    </Section>
  )
}

function GlideStrip({ visible }: { visible: boolean }) {
  const { t, language } = useLanguage()
  const width = 560
  const height = 150
  const barWidth = width / example.glide.length
  const paths = useMemo(() => {
    if (!visible) return []
    return example.glide.flatMap((point, i) => {
      const x = i * barWidth + 3
      const h = height - 30
      const equityH = h * point.equity_share
      const seed = seedFrom(`glide-${i}`)
      return [
        ...sketch((g) =>
          g.rectangle(x, 10 + (h - equityH), barWidth - 6, equityH, {
            ...PEN,
            strokeWidth: 1.2,
            fill: 'currentColor',
            fillStyle: 'hachure',
            hachureGap: 4,
            hachureAngle: -41,
            seed,
          }),
        ),
        ...sketch((g) =>
          g.rectangle(x, 10, barWidth - 6, h - equityH, {
            ...PEN,
            strokeWidth: 1.2,
            seed: seed + 1,
          }),
        ),
      ]
    })
  }, [visible, barWidth])
  const { pathProps } = useDrawOn({ duration: 1600, active: visible })
  const first = example.glide[0].equity_share
  const lastShare = example.glide[example.glide.length - 1].equity_share
  return (
    <figure className="m-0">
      <svg
        role="img"
        aria-label={t('glideSummary', {
          start: formatPercent(first, language),
          end: formatPercent(lastShare, language),
        })}
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full text-ink"
      >
        <RoughPaths paths={paths} pathProps={pathProps} />
        <text x={0} y={height - 2} className="font-hand" fontSize="14" fill="currentColor">
          {t('chartToday')}
        </text>
        <text
          x={width}
          y={height - 2}
          textAnchor="end"
          className="font-hand"
          fontSize="14"
          fill="currentColor"
        >
          {t('chartYear', { year: example.glide.length - 1 })}
        </text>
      </svg>
      <figcaption className="mt-2 flex flex-wrap gap-x-6 text-sm text-graphite">
        <span>
          <span
            aria-hidden="true"
            className="mr-1 inline-block h-3 w-5 bg-[repeating-linear-gradient(-41deg,var(--ink)_0_1px,transparent_1px_4px)] align-middle"
          />
          {t('glideShares')}
        </span>
        <span>
          <span
            aria-hidden="true"
            className="mr-1 inline-block h-3 w-5 border border-ink align-middle"
          />
          {t('glideSafer')}
        </span>
      </figcaption>
    </figure>
  )
}

export function GlideSection() {
  const { t } = useLanguage()
  const [ref, visible] = useInView<HTMLDivElement>()
  return (
    <Section
      title={t('sectionGlideTitle')}
      body={
        <>
          {t('sectionGlideBody')} {t('glideCalled')}{' '}
          <Term term="glide_path">{t('glidePathWord')}</Term>.
        </>
      }
    >
      <div ref={ref}>{visible && <GlideStrip visible={visible} />}</div>
    </Section>
  )
}

function Tick({ visible }: { visible: boolean }) {
  const paths = useMemo(
    () =>
      sketch((g) =>
        g.linearPath(
          [
            [4, 22],
            [14, 34],
            [38, 6],
          ],
          {
            ...PEN,
            stroke: 'var(--leaf)',
            strokeWidth: 3.2,
            roughness: 1.2,
            seed: seedFrom('tick'),
          },
        ),
      ),
    [],
  )
  const { pathProps } = useDrawOn({ duration: 500, delay: 700, active: visible })
  return (
    <svg aria-hidden="true" viewBox="0 0 42 40" className="h-10 w-10">
      <RoughPaths paths={paths} pathProps={pathProps} />
    </svg>
  )
}

export function LedgerSection() {
  const { t, language } = useLanguage()
  const [ref, visible] = useInView<HTMLDivElement>()
  const total = example.ledger_lines.reduce((sum, line) => sum + line.amount_cents, 0)
  return (
    <Section
      title={t('sectionLedgerTitle')}
      body={
        <>
          {t('sectionLedgerBody')} {t('ledgerCalled')}{' '}
          <Term term="double_entry">{t('doubleEntryWord')}</Term>.
        </>
      }
    >
      <div ref={ref} className="max-w-md">
        <p className="font-hand text-xl">
          {t('ledgerDeposit')} <Figure kind="money" value={-example.ledger_lines[0].amount_cents} />
        </p>
        <table className="mt-2 w-full border-collapse">
          <tbody>
            {example.ledger_lines.map((line) => (
              <tr key={line.account} className="border-b border-dashed border-graphite/60">
                <td className="py-1.5 pr-4">
                  {ASSET_LABELS[line.account]?.[language] ?? line.account}
                </td>
                <td className="py-1.5 text-right">
                  <Figure
                    kind="money"
                    value={line.amount_cents}
                    decimals={2}
                    className={line.amount_cents < 0 ? 'text-red-pen' : ''}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="mt-2 flex items-center justify-end gap-2 font-bold">
          {visible && <Tick visible={visible} />}
          <span>{t('ledgerBalanced', { total: formatMoney(total, language, 2) })}</span>
        </div>
      </div>
    </Section>
  )
}

export default function LandingSections() {
  return (
    <>
      <GoalSection />
      <GlideSection />
      <LedgerSection />
    </>
  )
}
