import { useLanguage } from '../lib/i18n'

export function LanguageToggle() {
  const { language, setLanguage, t } = useLanguage()
  const next = language === 'fr' ? 'en' : 'fr'
  return (
    <button
      type="button"
      onClick={() => setLanguage(next)}
      aria-label={t('languageToggle')}
      lang={next}
      className="min-h-11 min-w-11 px-2 font-bold"
    >
      <span aria-hidden="true">
        <span className={language === 'fr' ? 'underline decoration-2' : 'text-graphite'}>FR</span>
        {' / '}
        <span className={language === 'en' ? 'underline decoration-2' : 'text-graphite'}>EN</span>
      </span>
    </button>
  )
}
