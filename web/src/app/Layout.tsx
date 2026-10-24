import { NavLink, Outlet, ScrollRestoration } from 'react-router-dom'
import { LanguageToggle } from '../components/LanguageToggle'
import { CairnGlyph } from '../components/CairnGlyph'
import { ThemeToggle } from '../components/ThemeToggle'
import { useLanguage } from '../lib/i18n'
import { PebbleLayer } from '../pebble/PebbleLayer'
import { QuietToggle } from '../pebble/QuietToggle'

export function Layout() {
  const { t } = useLanguage()
  const links = [
    { to: '/start', label: t('navStart') },
    { to: '/simulate', label: t('navSimulate') },
    { to: '/goals', label: t('navGoals') },
  ]

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-paper focus:p-2"
      >
        {t('skipToContent')}
      </a>
      <header className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-8">
        <NavLink
          to="/"
          className="flex min-h-11 items-center gap-2 no-underline"
          aria-label={t('navHome')}
        >
          <CairnGlyph className="h-8 w-8 text-ink" />
          <span className="font-hand text-2xl">{t('appName')}</span>
        </NavLink>
        <nav aria-label="Main" className="order-3 w-full sm:order-none sm:w-auto">
          <ul className="flex flex-wrap gap-x-5">
            {links.map((link) => (
              <li key={link.to}>
                <NavLink
                  to={link.to}
                  className={({ isActive }) =>
                    `inline-flex min-h-11 items-center font-bold no-underline ${
                      isActive
                        ? 'underline decoration-highlighter decoration-[6px] underline-offset-[-1px]'
                        : ''
                    }`
                  }
                >
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <QuietToggle />
          <LanguageToggle />
          <ThemeToggle />
        </div>
      </header>

      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 pb-16 pt-4 sm:px-8">
        <Outlet />
      </main>

      <footer className="mx-auto flex w-full max-w-6xl flex-wrap items-baseline justify-between gap-x-6 gap-y-2 px-4 py-6 text-sm text-graphite sm:px-8">
        <span>{t('footer')}</span>
        <NavLink to="/support" className="underline decoration-dotted underline-offset-4">
          {t('supportLink')}
        </NavLink>
      </footer>
      <PebbleLayer />
      <ScrollRestoration />
    </div>
  )
}
