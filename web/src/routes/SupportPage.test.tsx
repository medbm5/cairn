import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'
import { worstMonth } from '../features/support/events'
import type { TimelineEvent } from '../lib/queries'
import { mockReducedMotion, renderWithProviders } from '../test/utils'
import { SupportPage } from './SupportPage'

const CLIENTS = [
  { id: 2, name: 'Camille Martin', email: 'camille.martin@example.com', goal_count: 1 },
  { id: 3, name: 'Thomas Bernard', email: 'thomas.bernard@example.com', goal_count: 2 },
]

const GOAL = { id: 4, name: 'A flat in Nantes' }

function event(
  id: number,
  type: string,
  date: string,
  amount: number,
  after: number,
): TimelineEvent {
  return {
    id,
    type,
    date,
    amount_cents: amount,
    goal: GOAL,
    goal_value_after_cents: after,
    payload:
      type === 'rebalance'
        ? { moved_cents: amount, transfers: { global_equity: -amount, euro_gov_bonds: amount } }
        : { by_asset: { global_equity: amount } },
  }
}

const TIMELINE = [
  event(10, 'deposit', '2026-02-01T09:00:00Z', 60_000, 1_000_000),
  event(11, 'market', '2026-02-28T17:00:00Z', 12_000, 1_012_000),
  event(12, 'deposit', '2026-03-01T09:00:00Z', 60_000, 1_072_000),
  event(13, 'fee', '2026-03-28T16:00:00Z', -1_500, 1_070_500),
  event(14, 'market', '2026-03-28T17:00:00Z', -150_000, 920_500),
  event(15, 'rebalance', '2026-03-28T17:00:00Z', 45_000, 920_500),
]

const SUMMARY = {
  id: 2,
  name: 'Camille Martin',
  email: 'camille.martin@example.com',
  profile: 'dynamic',
  total_balance_cents: 920_500,
  total_contributed_cents: 1_000_000,
  total_fees_cents: 1_500,
  last_activity: '2026-03-28T17:00:00Z',
  goals: [
    {
      ...GOAL,
      type: 'home',
      profile: 'dynamic',
      target_cents: 8_000_000,
      target_date: '2032-10-24',
      balance_cents: 920_500,
      contributed_cents: 1_000_000,
      fees_cents: 1_500,
    },
  ],
}

const ANSWER = {
  answer: {
    title: 'What happened in March 2026',
    body: 'In March 2026 the balance went from €10,120.00 to €9,205.00, a fall of €915.00.',
    analogy: null,
    terms_used: [],
    source: 'fallback',
  },
  focus: 'month_change',
  breakdown: {
    month: '2026-03',
    start_balance_cents: 1_012_000,
    end_balance_cents: 920_500,
    change_cents: -91_500,
    market_effect_cents: -150_000,
    deposits_cents: 60_000,
    fees_cents: 1_500,
    market_by_asset_cents: {
      global_equity: -150_000,
      emerging_equity: 0,
      euro_gov_bonds: 0,
      money_market: 0,
    },
  },
  event_ids: [12, 13, 14, 15],
}

function stubApi() {
  const calls: Request[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) => {
      calls.push(request.clone())
      const url = new URL(request.url)
      let body: unknown = {}
      if (url.pathname === '/support/clients') {
        const query = (url.searchParams.get('query') ?? '').toLowerCase()
        const items = CLIENTS.filter((c) => c.name.toLowerCase().includes(query))
        body = { items, total: items.length, page: 1, page_size: 20 }
      } else if (url.pathname.endsWith('/timeline')) body = TIMELINE
      else if (url.pathname.endsWith('/ask')) body = ANSWER
      else if (url.pathname === '/support/clients/2') body = SUMMARY
      return new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
      })
    }),
  )
  return calls
}

afterEach(() => vi.unstubAllGlobals())

test('the worst month is the one whose value fell, rebalances aside', () => {
  expect(worstMonth(TIMELINE)).toBe('2026-03')
  expect(worstMonth(TIMELINE.slice(0, 2))).toBeNull()
})

test('search renders matching clients, with an empty state until one is chosen', async () => {
  stubApi()
  const user = userEvent.setup()
  renderWithProviders(<SupportPage />, { route: '/support' })

  expect(screen.getByText('Search for a client to see their account history.')).toBeInTheDocument()
  await user.type(screen.getByLabelText('Find a client'), 'cam')
  expect(await screen.findByText('1 clients found')).toBeInTheDocument()
  const result = screen.getByRole('button', { name: /Camille Martin/ })
  expect(within(result).getByText(/camille\.martin@example\.com/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Thomas Bernard/ })).not.toBeInTheDocument()
})

test('asking a question highlights the events referenced in the answer', async () => {
  mockReducedMotion(true)
  const calls = stubApi()
  const user = userEvent.setup()
  renderWithProviders(<SupportPage />, { route: '/support?client=2' })

  expect(await screen.findByRole('heading', { name: 'Camille Martin' })).toBeInTheDocument()
  const row = (id: number) => document.querySelector(`[data-event-id="${id}"]`)!
  await waitFor(() => expect(row(10)).toBeInTheDocument())
  expect(row(12)).toHaveAttribute('data-highlighted', 'false')

  await user.click(screen.getByRole('button', { name: 'Why did the balance go down in March?' }))

  await waitFor(() => expect(row(12)).toHaveAttribute('data-highlighted', 'true'))
  for (const id of [13, 14, 15]) expect(row(id)).toHaveAttribute('data-highlighted', 'true')
  for (const id of [10, 11]) expect(row(id)).toHaveAttribute('data-highlighted', 'false')
  expect(screen.getByText('4 events highlighted in the timeline')).toBeInTheDocument()

  // The breakdown is exact and its parts add up to the change.
  expect(screen.getByText('How the balance changed in March 2026')).toBeInTheDocument()
  const breakdown = within(screen.getByRole('table'))
  expect(breakdown.getByRole('row', { name: /Market movements/ })).toHaveTextContent('-€1,500.00')
  expect(breakdown.getByRole('row', { name: /Deposits/ })).toHaveTextContent('€600.00')
  expect(breakdown.getByRole('row', { name: /Fees/ })).toHaveTextContent('-€15.00')
  expect(breakdown.getByRole('row', { name: /End of month/ })).toHaveTextContent('€9,205.00')

  const ask = calls.find((c) => c.url.endsWith('/support/clients/2/ask'))!
  expect(await ask.json()).toEqual({
    question: 'Why did the balance go down in March?',
    month: '2026-03',
    language: 'en',
  })
})
