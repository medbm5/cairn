import * as Sentry from '@sentry/react'

/** Start Sentry when VITE_SENTRY_DSN is set; otherwise do nothing. */
export function initSentry(): boolean {
  const dsn = import.meta.env.VITE_SENTRY_DSN
  if (!dsn) return false
  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    release: import.meta.env.VITE_RELEASE || undefined,
    tracesSampleRate: 0.1,
  })
  return true
}
