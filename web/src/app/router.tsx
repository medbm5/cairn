import { createBrowserRouter } from 'react-router-dom'
import { GoalDetailPage } from '../routes/GoalDetailPage'
import { GoalsPage } from '../routes/GoalsPage'
import { LandingPage } from '../routes/LandingPage'
import { NotFoundPage } from '../routes/NotFoundPage'
import { SimulatePage } from '../routes/SimulatePage'
import { StartPage } from '../routes/StartPage'
import { Layout } from './Layout'

export const routes = [
  {
    element: <Layout />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: '/start', element: <StartPage /> },
      { path: '/simulate', element: <SimulatePage /> },
      { path: '/goals', element: <GoalsPage /> },
      { path: '/goals/:id', element: <GoalDetailPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
