import { screen } from '@testing-library/react'
import { renderWithProviders } from '../test/utils'
import { Figure } from './Figure'

test('renders money with tabular figures in the current language', () => {
  renderWithProviders(<Figure kind="money" value={659_570} />, { language: 'en' })
  const figure = screen.getByText('€6,596')
  expect(figure).toHaveClass('figure')
})

test('renders percentages in French', () => {
  renderWithProviders(<Figure kind="percent" value={0.62} />, { language: 'fr' })
  expect(screen.getByText(/62\s%/)).toBeInTheDocument()
})
