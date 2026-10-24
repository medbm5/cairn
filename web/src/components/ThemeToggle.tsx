import { useMemo } from 'react'
import { useLanguage } from '../lib/i18n'
import { PEN, seedFrom, sketch } from '../lib/rough'
import { useTheme } from '../lib/theme'
import { RoughPaths } from './sketch/RoughPaths'

/** The theme switch: a pencil on the notebook, a stick of chalk on the blueprint. */
export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const { t } = useLanguage()
  const dark = theme === 'dark'
  const track = useMemo(
    () => sketch((g) => g.rectangle(2, 4, 52, 24, { ...PEN, seed: seedFrom('theme-track') })),
    [],
  )
  const nextName = dark ? t('themeLight') : t('themeDark')

  return (
    <button
      type="button"
      role="switch"
      aria-checked={dark}
      aria-label={t('themeToggle', { theme: nextName })}
      onClick={toggleTheme}
      className="inline-flex min-h-11 min-w-11 items-center gap-2 px-1 text-ink"
    >
      <svg
        aria-hidden="true"
        width="58"
        height="32"
        viewBox="0 0 58 32"
        className="overflow-visible"
      >
        <RoughPaths paths={track} />
        <g
          style={{
            transform: `translateX(${dark ? 28 : 0}px)`,
            transition: 'transform 200ms ease',
          }}
        >
          {dark ? (
            // Chalk: a short white stick with a dusty end.
            <g>
              <rect x="8" y="11" width="18" height="10" rx="3" style={{ fill: 'var(--ink)' }} />
              <circle cx="25" cy="16" r="3.5" style={{ fill: 'var(--ink)', opacity: 0.5 }} />
            </g>
          ) : (
            // Pencil: yellow body, sharpened tip.
            <g>
              <rect
                x="6"
                y="12"
                width="16"
                height="8"
                style={{ fill: 'var(--highlighter)', stroke: 'var(--ink)' }}
                strokeWidth="1.4"
              />
              <path
                d="M22 12 L29 16 L22 20 Z"
                style={{ fill: 'var(--paper)', stroke: 'var(--ink)' }}
                strokeWidth="1.4"
              />
              <path d="M27 15 L29 16 L27 17 Z" style={{ fill: 'var(--ink)' }} />
            </g>
          )}
        </g>
      </svg>
      <span className="font-hand text-sm">{dark ? t('themeDark') : t('themeLight')}</span>
    </button>
  )
}
