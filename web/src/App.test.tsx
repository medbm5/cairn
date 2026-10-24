import { render, screen } from '@testing-library/react'
import App from './App'

test('renders the app name and disclaimer', () => {
  render(<App />)
  expect(screen.getByRole('heading', { name: 'Cairn' })).toBeInTheDocument()
  expect(screen.getByText(/not investment advice/)).toBeInTheDocument()
})
