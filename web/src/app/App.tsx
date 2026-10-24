import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { ToastProvider } from '../components/Toast'
import { LanguageProvider } from '../lib/i18n'
import { ThemeProvider } from '../lib/theme'
import { PebbleProvider } from '../pebble/PebbleProvider'
import { router } from './router'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <LanguageProvider>
          <PebbleProvider>
            <ToastProvider>
              <RouterProvider router={router} />
            </ToastProvider>
          </PebbleProvider>
        </LanguageProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
