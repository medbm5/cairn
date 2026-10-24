import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { LazyMotion } from 'framer-motion'
import { RouterProvider } from 'react-router-dom'
import { ToastProvider } from '../components/Toast'
import { LanguageProvider } from '../lib/i18n'
import { ThemeProvider } from '../lib/theme'
import { PebbleProvider } from '../pebble/PebbleProvider'
import { router } from './router'

const loadMotionFeatures = () => import('./motionFeatures').then((module) => module.default)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <LazyMotion features={loadMotionFeatures} strict>
        <ThemeProvider>
          <LanguageProvider>
            <PebbleProvider>
              <ToastProvider>
                <RouterProvider router={router} />
              </ToastProvider>
            </PebbleProvider>
          </LanguageProvider>
        </ThemeProvider>
      </LazyMotion>
    </QueryClientProvider>
  )
}
