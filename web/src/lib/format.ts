import type { Language } from './i18n'

const LOCALES: Record<Language, string> = { fr: 'fr-FR', en: 'en-GB' }

export function formatMoney(cents: number, language: Language, decimals = 0): string {
  return new Intl.NumberFormat(LOCALES[language], {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(cents / 100)
}

export function formatPercent(fraction: number, language: Language, decimals = 0): string {
  return new Intl.NumberFormat(LOCALES[language], {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(fraction)
}

export function formatNumber(value: number, language: Language): string {
  return new Intl.NumberFormat(LOCALES[language]).format(value)
}

export function formatDate(iso: string, language: Language): string {
  return new Intl.DateTimeFormat(LOCALES[language], { year: 'numeric', month: 'long' }).format(
    new Date(iso),
  )
}

/** Years and months, e.g. "12 years" or "1 an et 3 mois". */
export function formatDuration(months: number, language: Language): string {
  const years = Math.floor(months / 12)
  const rest = months % 12
  const y = language === 'fr' ? (years === 1 ? 'an' : 'ans') : years === 1 ? 'year' : 'years'
  const m = language === 'fr' ? 'mois' : rest === 1 ? 'month' : 'months'
  const and = language === 'fr' ? 'et' : 'and'
  if (years === 0) return `${rest} ${m}`
  if (rest === 0) return `${years} ${y}`
  return `${years} ${y} ${and} ${rest} ${m}`
}
