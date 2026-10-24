import type { StringKey } from '../../lib/i18n'
import type { GoalType } from './goalTypes'

export interface GoalForm {
  type: GoalType | null
  name: string
  target: string // euros, as typed
  date: string // YYYY-MM
  monthly: string // euros, as typed
}

export type GoalErrors = Partial<Record<keyof GoalForm, StringKey>>

/** Read an amount typed in euros ("12 000", "12,000.50", "1234,5") as integer cents. */
export function parseEuros(text: string): number | null {
  let cleaned = text.replace(/[\s€']/g, '')
  if (cleaned === '') return null
  if (cleaned.includes(',') && cleaned.includes('.')) {
    // The last separator is the decimal one.
    cleaned =
      cleaned.lastIndexOf(',') > cleaned.lastIndexOf('.')
        ? cleaned.replace(/\./g, '').replace(',', '.')
        : cleaned.replace(/,/g, '')
  } else if (/,\d{1,2}$/.test(cleaned)) {
    cleaned = cleaned.replace(',', '.')
  } else {
    cleaned = cleaned.replace(/,/g, '')
  }
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return null
  return Math.round(Number(cleaned) * 100)
}

export function monthsUntil(yearMonth: string, today: Date): number | null {
  const match = /^(\d{4})-(\d{2})$/.exec(yearMonth)
  if (!match) return null
  return (Number(match[1]) - today.getFullYear()) * 12 + Number(match[2]) - (today.getMonth() + 1)
}

/** The questionnaire's horizon answer for a goal this many months away (option ids from the API). */
export function horizonAnswer(months: number): string {
  if (months < 36) return 'lt3'
  if (months < 60) return '3to5'
  if (months < 120) return '5to10'
  if (months < 240) return '10to20'
  return 'gt20'
}

/** The goal date as an ISO day: same day of month as today (capped at 28), so months are whole. */
export function targetDate(yearMonth: string, today: Date): string {
  const day = String(Math.min(today.getDate(), 28)).padStart(2, '0')
  return `${yearMonth}-${day}`
}

export function validateGoal(form: GoalForm, today: Date): GoalErrors {
  const errors: GoalErrors = {}
  if (!form.type) errors.type = 'errorType'
  if (!form.name.trim()) errors.name = 'errorName'
  const target = parseEuros(form.target)
  if (target === null || target <= 0) errors.target = 'errorTarget'
  const monthly = parseEuros(form.monthly)
  if (monthly === null || monthly < 0) errors.monthly = 'errorMonthly'
  const months = monthsUntil(form.date, today)
  if (months === null || months < 12 || months > 480) errors.date = 'errorDate'
  return errors
}
