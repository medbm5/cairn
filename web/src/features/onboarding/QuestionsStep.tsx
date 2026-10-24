import { useState } from 'react'
import { ProgressLine } from '../../components/ProgressLine'
import { Skeleton } from '../../components/Skeleton'
import { SketchButton } from '../../components/sketch/SketchButton'
import { useLanguage } from '../../lib/i18n'
import { useQuestionnaire } from '../../lib/queries'
import { usePebble } from '../../pebble/PebbleProvider'

/** The six risk questions, one per screen, with a hand-drawn progress line. */
export function QuestionsStep({
  answers,
  onAnswer,
  onBack,
  onDone,
}: {
  answers: Record<string, string>
  onAnswer: (questionId: string, optionId: string) => void
  onBack: () => void
  onDone: () => void
}) {
  const { t, language } = useLanguage()
  const pebble = usePebble()
  const questionnaire = useQuestionnaire(language)
  const [index, setIndex] = useState(0)

  if (questionnaire.isPending) return <Skeleton id="questions-loading" lines={4} />
  if (questionnaire.isError) {
    return (
      <div role="alert">
        <p>{t('errorBody')}</p>
        <SketchButton sketchId="questions-retry" onClick={() => questionnaire.refetch()}>
          {t('tryAgain')}
        </SketchButton>
      </div>
    )
  }

  const questions = questionnaire.data
  const question = questions[index]
  const chosen = answers[question.id]
  const last = index === questions.length - 1

  const choose = (optionId: string, position: number) => {
    onAnswer(question.id, optionId)
    // A brief reaction: Pebble cheers at bolder answers and ponders cautious ones.
    pebble.setState(position >= question.options.length / 2 ? 'cheer' : 'think')
    window.setTimeout(() => pebble.setState('idle'), 900)
  }

  return (
    <div className="flex max-w-2xl flex-col gap-5">
      <div>
        <p className="mb-1 text-sm text-graphite">
          {t('questionCounter', { n: index + 1, total: questions.length })}
        </p>
        <ProgressLine
          id="questions-progress"
          value={index + (chosen ? 1 : 0)}
          max={questions.length}
          label={t('questionCounter', { n: index + 1, total: questions.length })}
        />
      </div>
      <fieldset>
        <legend className="mb-4 font-hand text-2xl">{question.text}</legend>
        <div className="flex flex-col gap-2">
          {question.options.map((option, position) => (
            <label
              key={option.id}
              className={`flex min-h-11 cursor-pointer items-center gap-3 border-2 border-dashed px-4 py-2 ${
                chosen === option.id
                  ? 'border-solid border-ink bg-highlighter/35 font-bold'
                  : 'border-graphite/60'
              }`}
            >
              <input
                type="radio"
                name={question.id}
                value={option.id}
                checked={chosen === option.id}
                onChange={() => choose(option.id, position)}
                className="h-5 w-5 accent-[var(--ink)]"
              />
              {option.text}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="flex flex-wrap gap-3">
        <SketchButton
          sketchId="questions-back"
          variant="quiet"
          onClick={() => (index === 0 ? onBack() : setIndex(index - 1))}
        >
          {t('back')}
        </SketchButton>
        <SketchButton
          sketchId="questions-next"
          variant="primary"
          disabled={!chosen}
          onClick={() => (last ? onDone() : setIndex(index + 1))}
        >
          {t('continue')}
        </SketchButton>
      </div>
    </div>
  )
}
