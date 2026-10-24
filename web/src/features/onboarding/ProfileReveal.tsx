import { useEffect } from 'react'
import { AllocationBar } from '../../charts/AllocationBar'
import { Skeleton } from '../../components/Skeleton'
import { SketchButton } from '../../components/sketch/SketchButton'
import { useLanguage, type StringKey } from '../../lib/i18n'
import { useScoreQuestionnaire, type Profile } from '../../lib/queries'
import { PebbleInline } from '../../pebble/PebbleInline'
import { usePebble, usePebbleAnchor } from '../../pebble/PebbleProvider'

/** Step 3: the profile is revealed as a stacked bar that draws itself; Pebble cheers, then explains. */
export function ProfileReveal({
  answers,
  creating,
  createError,
  onConfirm,
  onBack,
}: {
  answers: Record<string, string>
  creating: boolean
  createError: string | null
  onConfirm: (profile: Profile) => void
  onBack: () => void
}) {
  const { t } = useLanguage()
  const pebble = usePebble()
  const anchor = usePebbleAnchor('profile-allocation')
  const score = useScoreQuestionnaire()
  const { mutate } = score

  useEffect(() => {
    mutate(answers)
  }, [answers, mutate])

  const profile = score.data?.profile
  useEffect(() => {
    if (!profile) return
    pebble.setState('cheer')
    const timer = window.setTimeout(() => {
      pebble.setState('idle')
      pebble.say({
        topic: 'allocation',
        facts: { profile: profile.key, weights: profile.weights },
        anchorId: 'profile-allocation',
      })
    }, 1300)
    return () => window.clearTimeout(timer)
    // Once per revealed profile.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile?.key])

  if (score.isError) {
    return (
      <div role="alert" className="flex max-w-xl flex-col items-start gap-3">
        <p>{t('scoreFailed')}</p>
        <SketchButton sketchId="score-retry" onClick={() => mutate(answers)}>
          {t('tryAgain')}
        </SketchButton>
      </div>
    )
  }
  if (!profile) return <Skeleton id="profile-loading" lines={3} />

  return (
    <div className="flex max-w-2xl flex-col gap-5">
      <h2>{t('profileRevealTitle', { name: t(`profile_${profile.key}` as StringKey) })}</h2>
      <p>{t('profileRevealIntro')}</p>
      <div ref={anchor}>
        <AllocationBar id={`reveal-${profile.key}`} weights={profile.weights} drawOn />
      </div>
      <PebbleInline anchorId="profile-allocation" />
      {createError && (
        <p role="alert" className="font-bold text-red-pen">
          {t('createFailed', { message: createError })}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <SketchButton sketchId="reveal-back" variant="quiet" onClick={onBack} disabled={creating}>
          {t('back')}
        </SketchButton>
        <SketchButton
          sketchId="reveal-confirm"
          variant="primary"
          disabled={creating}
          onClick={() => onConfirm(profile)}
        >
          {creating ? t('creatingGoal') : t('seeProjection')}
        </SketchButton>
      </div>
    </div>
  )
}
