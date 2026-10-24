import { createBrowserRouter } from 'react-router-dom'
import { LandingPage } from '../routes/LandingPage'
import { NotFoundPage } from '../routes/NotFoundPage'
import { Layout } from './Layout'

// The landing page ships in the main bundle; other screens load on demand.
export const routes = [
  {
    element: <Layout />,
    children: [
      { path: '/', element: <LandingPage /> },
      {
        path: '/start',
        lazy: async () => ({ Component: (await import('../routes/StartPage')).StartPage }),
      },
      {
        path: '/simulate',
        lazy: async () => ({ Component: (await import('../routes/SimulatePage')).SimulatePage }),
      },
      {
        path: '/goals',
        lazy: async () => ({ Component: (await import('../routes/GoalsPage')).GoalsPage }),
      },
      {
        path: '/goals/:id',
        lazy: async () => ({
          Component: (await import('../routes/GoalDetailPage')).GoalDetailPage,
        }),
      },
      {
        path: '/support',
        lazy: async () => ({ Component: (await import('../routes/SupportPage')).SupportPage }),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
