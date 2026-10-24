import { useEffect, useId, useRef, type ReactNode } from 'react'
import { useLanguage } from '../lib/i18n'

interface SheetProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}

/** A bottom sheet: a sheet of paper that slides up from the bottom of the screen. */
export function Sheet({ open, onClose, title, children }: SheetProps) {
  const { t } = useLanguage()
  const titleId = useId()
  const panel = useRef<HTMLDivElement>(null)
  const returnFocus = useRef<Element | null>(null)

  useEffect(() => {
    if (!open) return
    returnFocus.current = document.activeElement
    panel.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      if (returnFocus.current instanceof HTMLElement) returnFocus.current.focus()
    }
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      <div aria-hidden="true" className="absolute inset-0 bg-ink/25" onClick={onClose} />
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="relative max-h-[85vh] w-full max-w-xl overflow-y-auto rounded-t-2xl border-2 border-b-0 border-ink bg-paper p-5 pb-8 shadow-lg"
      >
        <div className="mb-3 flex items-start justify-between gap-4">
          <h2 id={titleId} className="text-2xl">
            {title}
          </h2>
          <button type="button" onClick={onClose} className="min-h-11 px-2 font-bold underline">
            {t('close')}
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
