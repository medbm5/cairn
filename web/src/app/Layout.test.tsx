import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { renderWithProviders } from '../test/utils'
import { Layout } from './Layout'

test('shows navigation, the disclaimer and switches language', async () => {
  renderWithProviders(
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<p>Page</p>} />
      </Route>
    </Routes>,
  )
  expect(screen.getByRole('link', { name: 'Simulator' })).toBeInTheDocument()
  expect(
    screen.getByText('Demo project. Simplified assumptions, not investment advice.'),
  ).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Passer en français' }))
  expect(screen.getByRole('link', { name: 'Simulateur' })).toBeInTheDocument()
})

test('theme switch toggles the blueprint theme', async () => {
  renderWithProviders(<Layout />)
  const toggle = screen.getByRole('switch', { name: /theme/ })
  const before = document.documentElement.dataset.theme
  await userEvent.click(toggle)
  expect(document.documentElement.dataset.theme).not.toBe(before)
})
