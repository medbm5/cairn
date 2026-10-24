import { useEffect, useState } from 'react'
import { useLanguage } from '../lib/i18n'
import { useReducedMotion } from '../lib/motion'
import { usePebble } from './PebbleProvider'
import { termName } from './terms'

/**
 * Reveal text a few characters at a time, like handwriting. Instant with reduced motion.
 * Callers key the component by its text, so a new text starts a fresh reveal.
 */
function useHandwriting(text: string, enabled: boolean): string {
  const reduced = useReducedMotion()
  const animate = enabled && !reduced
  const [shown, setShown] = useState(0)
  useEffect(() => {
    if (!animate) return
    // Whole text in at most about 1.6 s, whatever its length.
    const step = Math.max(1, Math.ceil(text.length / 80))
    const timer = window.setInterval(() => {
      setShown((n) => {
        if (n + step >= text.length) window.clearInterval(timer)
        return Math.min(text.length, n + step)
      })
    }, 20)
    return () => window.clearInterval(timer)
  }, [text, animate])
  return animate ? text.slice(0, shown) : text
}

/**
 * The words of the current message: title, body, analogy, tappable terms and the buttons.
 * Shared by the speech bubble, the mobile sheet and the quiet inline panel.
 */
export function SpeechContent({ handwritten }: { handwritten: boolean }) {
  const { t, language } = useLanguage()
  const pebble = usePebble()
  const { current, explanation, explanationLoading, explanationError } = pebble
  if (!current) return null

  const request = current.request
  let title: string | undefined
  let body: string
  let analogy: string | null | undefined
  let terms: string[] = []
  if ('text' in request) {
    title = request.title
    body = request.text
  } else if (explanationLoading) {
    body = t('thinking')
  } else if (explanationError || !explanation) {
    body = t('explainFailed')
  } else {
    title = explanation.title
    body = explanation.body
    analogy = explanation.analogy
    terms = explanation.terms_used.filter((term) => !('term' in request && request.term === term))
  }

  const canTellMore =
    'topic' in request && (request.level ?? 'simple') === 'simple' && !!explanation

  return (
    <div className={handwritten ? 'font-hand text-[1.05rem] leading-snug' : ''}>
      {title && <p className="mb-1 text-lg font-bold">{title}</p>}
      <SpeechText key={body} text={body} handwritten={handwritten} />
      {analogy && <p className="mt-2 italic text-graphite">{analogy}</p>}
      {terms.length > 0 && (
        <div className="mt-3 text-sm">
          <span className="text-graphite">{t('wordsInThis')} </span>
          {terms.map((term) => (
            <button
              key={term}
              type="button"
              onClick={() => pebble.explainTerm(term)}
              className="mr-2 min-h-8 underline decoration-dotted decoration-2 underline-offset-4"
            >
              {termName(term, language)}
            </button>
          ))}
        </div>
      )}
      <div className="mt-3 flex flex-wrap gap-3 font-body">
        <button
          type="button"
          onClick={pebble.dismiss}
          className="min-h-11 rounded-md border-2 border-ink px-4 font-bold"
        >
          {pebble.queueLength > 1 && 'text' in request ? t('nextStep') : t('gotIt')}
        </button>
        {canTellMore && (
          <button
            type="button"
            onClick={pebble.tellMeMore}
            className="min-h-11 px-2 font-bold underline"
          >
            {t('tellMeMore')}
          </button>
        )}
      </div>
    </div>
  )
}

function SpeechText({ text, handwritten }: { text: string; handwritten: boolean }) {
  const visible = useHandwriting(text, handwritten)
  return (
    <p>
      {/* Screen readers get the whole text at once; the reveal is visual only. */}
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">{visible}</span>
    </p>
  )
}
