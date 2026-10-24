import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { useState, type ReactElement, type ReactNode } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { ToastProvider } from '../components/Toast'
import { LanguageProvider, type Language } from '../lib/i18n'
import { ThemeProvider } from '../lib/theme'
import { PebbleProvider } from '../pebble/PebbleProvider'
import type { Explanation, ExplainRequest } from '../lib/queries'

export function Providers({
  children,
  language = 'en',
  route = '/',
  explain = fakeExplain,
}: {
  children: ReactNode
  language?: Language
  route?: string
  explain?: (request: ExplainRequest) => Promise<Explanation>
}) {
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: false } } }),
  )
  // A data router, as in the app, so hooks such as ScrollRestoration work.
  const [router] = useState(() =>
    createMemoryRouter([{ path: '*', element: children }], { initialEntries: [route] }),
  )
  return (
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <LanguageProvider initial={language}>
          <PebbleProvider explain={explain} pingApi={() => Promise.resolve()}>
            <ToastProvider>
              <RouterProvider router={router} />
            </ToastProvider>
          </PebbleProvider>
        </LanguageProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

/** A stand-in for POST /explain: echoes the topic so tests can see what was asked. */
export async function fakeExplain(request: ExplainRequest): Promise<Explanation> {
  return {
    title: `About ${request.term ?? request.topic}`,
    body: `Plain words about ${request.term ?? request.topic} (${request.level ?? 'simple'}).`,
    analogy: null,
    terms_used: [],
    source: 'fallback',
  }
}

export function renderWithProviders(
  ui: ReactElement,
  options: {
    language?: Language
    route?: string
    explain?: (request: ExplainRequest) => Promise<Explanation>
  } = {},
) {
  return render(<Providers {...options}>{ui}</Providers>)
}

/** Make matchMedia report prefers-reduced-motion (jsdom has no matchMedia). */
export function mockReducedMotion(reduced: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: reduced && query.includes('prefers-reduced-motion'),
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
}
