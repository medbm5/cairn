import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'
import { PebbleLayer } from '../pebble/PebbleLayer'
import { mockReducedMotion, renderWithProviders } from '../test/utils'
import { SimulatePage } from './SimulatePage'

const months = [0, 60, 120, 180]
const SIMULATION = {
  seed: 42,
  paths: 2000,
  months,
  p10: [500_000, 2_000_000, 3_500_000, 5_000_000],
  p25: [500_000, 2_300_000, 4_200_000, 6_100_000],
  p50: [500_000, 2_600_000, 5_000_000, 7_500_000],
  p75: [500_000, 2_900_000, 5_800_000, 8_900_000],
  p90: [500_000, 3_300_000, 6_700_000, 10_500_000],
  contributed: [500_000, 2_300_000, 4_100_000, 5_900_000],
  success_probability: 0.12,
}

afterEach(() => vi.unstubAllGlobals())

test('draws the projection, states it in text and lets Pebble explain it', async () => {
  mockReducedMotion(true)
  window.localStorage.setItem('cairn.tour.simulate', 'seen')
  const bodies: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) => {
      bodies.push(await request.clone().text())
      return new Response(JSON.stringify(SIMULATION), {
        headers: { 'Content-Type': 'application/json' },
      })
    }),
  )
  const user = userEvent.setup()
  renderWithProviders(
    <>
      <SimulatePage />
      <PebbleLayer />
    </>,
  )

  expect(await screen.findByRole('img', { name: /Middle scenario: €75,000/ })).toBeInTheDocument()
  expect(screen.getByText('12%')).toBeInTheDocument()
  const sent = JSON.parse(bodies[0])
  expect(sent).toMatchObject({ glide_path: true, profile: 'balanced', horizon_months: 180 })

  await user.click(screen.getByRole('button', { name: 'What does this mean?' }))
  // Once for screen readers, once as the visible handwriting.
  expect(await screen.findAllByText('Plain words about projection (simple).')).not.toHaveLength(0)
})

test('debounces slider changes into a new request with the new inputs', async () => {
  mockReducedMotion(true)
  const bodies: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) => {
      bodies.push(await request.clone().text())
      return new Response(JSON.stringify(SIMULATION), {
        headers: { 'Content-Type': 'application/json' },
      })
    }),
  )
  const user = userEvent.setup()
  renderWithProviders(<SimulatePage />)
  await screen.findByRole('img', { name: /Middle scenario/ })

  await user.click(screen.getByRole('radio', { name: 'Bold' }))
  await waitFor(() => expect(bodies.some((b) => JSON.parse(b).profile === 'bold')).toBe(true))
})
