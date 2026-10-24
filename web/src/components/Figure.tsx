import { formatMoney, formatPercent, formatNumber } from '../lib/format'
import { useLanguage } from '../lib/i18n'

interface FigureProps {
  value: number
  /** money: integer cents; percent: a fraction (0.25 = 25%); number: as is. */
  kind: 'money' | 'percent' | 'number'
  decimals?: number
  className?: string
}

/** An exact figure: crisp type with tabular numbers, never hand-drawn. */
export function Figure({ value, kind, decimals, className = '' }: FigureProps) {
  const { language } = useLanguage()
  const text =
    kind === 'money'
      ? formatMoney(value, language, decimals)
      : kind === 'percent'
        ? formatPercent(value, language, decimals)
        : formatNumber(value, language)
  return <span className={`figure whitespace-nowrap ${className}`}>{text}</span>
}
