import { fireEvent, screen } from '@testing-library/react'
import { mockReducedMotion, renderWithProviders } from '../test/utils'
import { LandingPage } from './LandingPage'

test('hero shows the headline and the slider reshapes the projection', async () => {
  mockReducedMotion(true)
  renderWithProviders(<LandingPage />)
  expect(
    screen.getByRole('heading', { name: 'See where your savings could take you.' }),
  ).toBeInTheDocument()

  const slider = screen.getByRole('slider', { name: 'Monthly savings' })
  const chart = await screen.findByRole('img', { name: /Projection over 15 years/ })
  const before = chart.getAttribute('aria-label')
  fireEvent.change(slider, { target: { value: '20' } })
  expect(slider).toHaveAttribute('aria-valuetext', '€600')
  expect(chart.getAttribute('aria-label')).not.toBe(before)
  expect(screen.getByRole('link', { name: 'Plan my first goal' })).toHaveAttribute('href', '/start')
})
