/** Start Sentry when VITE_SENTRY_DSN is set; otherwise do nothing (and never download it). */
export async function initSentry(): Promise<boolean> {
  const dsn = import.meta.env.VITE_SENTRY_DSN
  if (!dsn) return false
  const Sentry = await import('@sentry/react')
  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    release: import.meta.env.VITE_RELEASE || undefined,
    tracesSampleRate: 0.1,
  })
  return true
}
