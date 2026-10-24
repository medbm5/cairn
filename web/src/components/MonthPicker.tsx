import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { useLanguage } from '../lib/i18n'
import { SketchBox } from './sketch/SketchBox'

const LOCALES = { fr: 'fr-FR', en: 'en-GB' } as const

interface MonthPickerProps {
  label: string
  hint?: string
  error?: string
  /** YYYY-MM, or '' when nothing is picked yet. */
  value: string
  onChange: (value: string) => void
  /** Earliest and latest pickable months, as YYYY-MM. */
  min: string
  max: string
  onFocus?: () => void
}

const parse = (yearMonth: string) => {
  const match = /^(\d{4})-(\d{2})$/.exec(yearMonth)
  return match ? { year: Number(match[1]), month: Number(match[2]) } : null
}
const key = (year: number, month: number) => `${year}-${String(month).padStart(2, '0')}`

/** A month-and-year picker drawn like the other notebook fields: a button that opens a calendar of months. */
export function MonthPicker({
  label,
  hint,
  error,
  value,
  onChange,
  min,
  max,
  onFocus,
}: MonthPickerProps) {
  const { language, t } = useLanguage()
  const id = useId()
  const hintId = `${id}-hint`
  const errorId = `${id}-error`
  const panelId = `${id}-panel`
  const describedBy = [hint && hintId, error && errorId].filter(Boolean).join(' ') || undefined

  const first = parse(min)!
  const last = parse(max)!
  const picked = parse(value)
  const [open, setOpen] = useState(false)
  const [viewYear, setViewYear] = useState(picked?.year ?? first.year)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  const months = useMemo(() => {
    const short = new Intl.DateTimeFormat(LOCALES[language], { month: 'short' })
    const long = new Intl.DateTimeFormat(LOCALES[language], { month: 'long', year: 'numeric' })
    return Array.from({ length: 12 }, (_, i) => ({
      short: short.format(new Date(2000, i, 1)),
      long: (year: number) => long.format(new Date(year, i, 1)),
    }))
  }, [language])

  const display = picked ? months[picked.month - 1].long(picked.year) : t('datePlaceholder')

  const close = (refocus: boolean) => {
    setOpen(false)
    if (refocus) triggerRef.current?.focus()
  }

  const toggle = () => {
    if (!open) setViewYear(picked?.year ?? first.year)
    setOpen(!open)
  }

  // Move focus into the panel when it opens, onto the picked month if it is in view.
  useEffect(() => {
    if (!open) return
    const panel = panelRef.current
    const target =
      panel?.querySelector<HTMLButtonElement>('button[aria-pressed="true"]') ??
      panel?.querySelector<HTMLButtonElement>('button[data-month]:not(:disabled)')
    target?.focus()
    // Only on open: changing year keeps focus where the person put it.
  }, [open])

  // Close on a click outside.
  useEffect(() => {
    if (!open) return
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) close(false)
    }
    document.addEventListener('pointerdown', onPointer)
    return () => document.removeEventListener('pointerdown', onPointer)
  }, [open])

  const years = Array.from({ length: last.year - first.year + 1 }, (_, i) => first.year + i)
  const choose = (month: number) => {
    onChange(key(viewYear, month))
    close(true)
  }

  return (
    <div ref={rootRef} className="relative flex flex-col gap-1">
      <span id={`${id}-label`} className="font-bold">
        {label}
      </span>
      {hint && (
        <p id={hintId} className="text-sm text-graphite">
          {hint}
        </p>
      )}
      <button
        ref={triggerRef}
        type="button"
        aria-labelledby={`${id}-label ${id}-value`}
        aria-describedby={describedBy}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-invalid={error ? true : undefined}
        onClick={toggle}
        onFocus={onFocus}
        className="figure flex min-h-11 items-center justify-between gap-2 border-0 border-b-2 border-dashed border-graphite bg-transparent px-1 text-left text-lg focus:border-solid focus:border-ink"
      >
        <span id={`${id}-value`} className={picked ? 'text-ink' : 'text-graphite/70'}>
          {display}
        </span>
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-graphite">
          <path
            d="M4 6.5h16v13H4zM4 10.5h16M8.5 4v4M15.5 4v4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      {error && (
        <p id={errorId} role="alert" className="text-sm font-bold text-red-pen">
          {error}
        </p>
      )}

      {open && (
        <div
          ref={panelRef}
          id={panelId}
          role="dialog"
          aria-label={label}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.stopPropagation()
              close(true)
            }
          }}
          className="absolute left-0 top-full z-20 mt-2 w-full max-w-xs"
        >
          <SketchBox id="month-picker" className="bg-paper p-3 shadow-lg">
            <div className="mb-3 flex items-center justify-between gap-2">
              <button
                type="button"
                aria-label={t('previousYear')}
                disabled={viewYear <= first.year}
                onClick={() => setViewYear(viewYear - 1)}
                className="min-h-11 min-w-11 rounded text-xl disabled:opacity-30"
              >
                ‹
              </button>
              <select
                aria-label={t('yearLabel')}
                value={viewYear}
                onChange={(event) => setViewYear(Number(event.target.value))}
                className="figure min-h-11 cursor-pointer border-0 bg-transparent text-center text-lg font-bold text-ink"
              >
                {years.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
              <button
                type="button"
                aria-label={t('nextYear')}
                disabled={viewYear >= last.year}
                onClick={() => setViewYear(viewYear + 1)}
                className="min-h-11 min-w-11 rounded text-xl disabled:opacity-30"
              >
                ›
              </button>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {months.map((month, index) => {
                const monthKey = key(viewYear, index + 1)
                const selected = monthKey === value
                const outOfRange = monthKey < min || monthKey > max
                return (
                  <button
                    key={index}
                    type="button"
                    data-month
                    aria-label={month.long(viewYear)}
                    aria-pressed={selected}
                    disabled={outOfRange}
                    onClick={() => choose(index + 1)}
                    className={`min-h-11 rounded px-1 text-sm capitalize ${
                      selected ? 'bg-highlighter/60 font-bold' : 'hover:bg-highlighter/25'
                    } disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-transparent`}
                  >
                    {month.short.replace('.', '')}
                  </button>
                )
              })}
            </div>
          </SketchBox>
        </div>
      )}
    </div>
  )
}
