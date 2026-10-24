import { SketchLink } from '../components/sketch/SketchButton'
import { useLanguage } from '../lib/i18n'

export function NotFoundPage() {
  const { t } = useLanguage()
  return (
    <section className="max-w-xl py-10">
      <h1>{t('notFoundTitle')}</h1>
      <p className="mb-6 mt-3">{t('notFoundBody')}</p>
      <SketchLink sketchId="not-found-home" to="/">
        {t('goHome')}
      </SketchLink>
    </section>
  )
}
