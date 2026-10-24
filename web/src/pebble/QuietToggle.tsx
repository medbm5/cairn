import { useLanguage } from '../lib/i18n'
import { usePebble } from './PebbleProvider'

/** The visible "Quiet Pebble" switch: hides Pebble and shows explanations as plain panels. */
export function QuietToggle() {
  const { quiet, setQuiet } = usePebble()
  const { t } = useLanguage()
  return (
    <label
      className="inline-flex min-h-11 cursor-pointer items-center gap-2 px-1 text-sm font-bold"
      title={t('quietPebbleHint')}
    >
      <input
        type="checkbox"
        role="switch"
        checked={quiet}
        onChange={(event) => setQuiet(event.target.checked)}
        className="h-5 w-5 accent-[var(--ink)]"
      />
      {t('quietPebble')}
    </label>
  )
}
