import { screen, waitFor, within } from '@testing-library/react'
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

const SOLUTION = {
  target_probability: 0.8,
  current_probability: 0.12,
  seed: 2026,
  paths: 2000,
  options: [
    {
      lever: 'target',
      value: 70_000_00,
      current: 100_000_00,
      delta: -30_000_00,
      relative_change: 0.3,
      success_probability: 0.81,
      feasible: true,
      target_date: null,
    },
    {
      lever: 'horizon',
      value: 252,
      current: 180,
      delta: 72,
      relative_change: 0.4,
      success_probability: 0.82,
      feasible: true,
      target_date: '2047-10-25',
    },
    {
      lever: 'contribution',
      value: 450_00,
      current: 300_00,
      delta: 150_00,
      relative_change: 0.5,
      success_probability: 0.83,
      feasible: true,
      target_date: null,
    },
  ],
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

test('the solver shows three options, previews one on the chart and applies it', async () => {
  mockReducedMotion(true)
  window.localStorage.setItem('cairn.tour.simulate', 'seen')
  const requests: { url: string; body: Record<string, unknown> }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) => {
      const body = JSON.parse((await request.clone().text()) || '{}')
      requests.push({ url: request.url, body })
      const data = request.url.endsWith('/simulations/solve') ? SOLUTION : SIMULATION
      return new Response(JSON.stringify(data), {
        headers: { 'Content-Type': 'application/json' },
      })
    }),
  )
  const asked: string[] = []
  const user = userEvent.setup()
  renderWithProviders(
    <>
      <SimulatePage />
      <PebbleLayer />
    </>,
    {
      explain: async (request) => {
        asked.push(request.topic)
        return {
          title: 'Ways to reach 80%',
          body: `Plain words about ${request.topic}.`,
          analogy: null,
          terms_used: [],
          source: 'fallback',
        }
      },
    },
  )
  await screen.findByRole('img', { name: /Middle scenario/ })

  await user.click(screen.getByRole('button', { name: 'How do I get there?' }))
  expect(
    await screen.findByRole('heading', { name: 'Three ways to reach 80%' }),
  ).toBeInTheDocument()
  const solve = requests.find((r) => r.url.endsWith('/simulations/solve'))!
  expect(solve.body).toMatchObject({
    monthly_contribution_cents: 300_00,
    horizon_months: 180,
    contribution_step_cents: 25_00,
    horizon_step_months: 12,
  })
  // Smallest change first, as the API sorted them; each with its chance.
  const cards = screen.getAllByRole('listitem').filter((li) => li.className.includes('note-in'))
  expect(cards.map((card) => within(card).getByText(/^(Aim|Push|Save)/).textContent)).toEqual([
    'Aim for €70,000',
    'Push the date to October 2047',
    'Save €450 a month',
  ])
  expect(within(cards[2]).getByText('83%')).toBeInTheDocument()
  expect(within(cards[2]).getByText('€150 more a month than now')).toBeInTheDocument()

  // Hovering an option re-draws the chart with it, using the solver's seed and path count.
  await user.hover(cards[2])
  await waitFor(() =>
    expect(
      requests.some(
        (r) =>
          r.url.endsWith('/simulations') &&
          r.body.monthly_contribution_cents === 450_00 &&
          r.body.seed === 2026,
      ),
    ).toBe(true),
  )

  await user.click(screen.getByRole('button', { name: 'Explain these options' }))
  await waitFor(() => expect(asked).toContain('solver'))

  await user.click(screen.getByRole('button', { name: 'Use this plan: Save €450 a month' }))
  await waitFor(() =>
    expect(
      requests.some(
        (r) =>
          r.url.endsWith('/simulations') &&
          r.body.monthly_contribution_cents === 450_00 &&
          r.body.seed === 42,
      ),
    ).toBe(true),
  )
  expect(screen.getByRole('slider', { name: /Monthly savings/ })).toHaveValue('45000')
})
