import { lazy, Suspense } from 'react'
import { SketchLink } from '../components/sketch/SketchButton'
import { HeroSketch } from '../features/landing/HeroSketch'
import { useLanguage } from '../lib/i18n'
import { useLenis } from '../lib/useLenis'

// Below-the-fold sections load after the hero.
const LandingSections = lazy(() => import('../features/landing/LandingSections'))

export function LandingPage() {
  const { t } = useLanguage()
  useLenis()
  return (
    <>
      <HeroSketch />
      <Suspense fallback={<div className="min-h-[60vh]" />}>
        <LandingSections />
      </Suspense>
      <section className="py-14 text-center">
        <h2>{t('ctaTitle')}</h2>
        <div className="mt-6">
          <SketchLink sketchId="landing-cta" to="/start" variant="primary" className="text-lg">
            {t('ctaPlan')}
          </SketchLink>
        </div>
      </section>
    </>
  )
}
