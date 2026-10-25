import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { afterEach, vi } from 'vitest'
import { entryAmount, nextMilestone } from '../features/goals/ledger'
import type { JournalEntry } from '../lib/queries'
import { mockReducedMotion, renderWithProviders } from '../test/utils'
import { GoalDetailPage } from './GoalDetailPage'
import { GoalsPage } from './GoalsPage'

const GOAL = {
  id: 1,
  name: 'Retirement top-up',
  type: 'retirement',
  target_cents: 15_000_000,
  target_date: '2038-06-01',
  monthly_contribution_cents: 40_000,
  profile: 'dynamic',
  created_at: '2026-10-24T20:00:00Z',
}
const WEIGHTS = {
  global_equity: 0.6,
  emerging_equity: 0.15,
  euro_gov_bonds: 0.2,
  money_market: 0.05,
}
const months = [0, 12, 24]
const SIMULATION = {
  seed: 1,
  paths: 2000,
  months,
  p10: [0, 400_000, 800_000],
  p25: [0, 450_000, 900_000],
  p50: [0, 480_000, 980_000],
  p75: [0, 510_000, 1_050_000],
  p90: [0, 560_000, 1_150_000],
  contributed: [0, 480_000, 960_000],
  success_probability: 0,
}
const option = (lever: string, value: number, current: number, target_date: string | null) => ({
  lever,
  value,
  current,
  delta: value - current,
  relative_change: Math.abs(value - current) / current,
  success_probability: 0.8,
  feasible: true,
  target_date,
})
const SOLUTION = {
  target_probability: 0.8,
  current_probability: 0,
  seed: 2026,
  paths: 2000,
  options: [
    option('horizon', 150, 24, '2039-04-25'),
    option('contribution', 6_000_00, 400_00, null),
    option('target', 9_000_00, 150_000_00, null),
  ],
}

function respond(url: string, method: string): unknown {
  if (url.endsWith('/solve')) return SOLUTION
  if (url.endsWith('/simulations')) return SIMULATION
  if (url.endsWith('/goals') && method === 'GET') return []
  if (url.includes('/deposits'))
    return {
      id: 9,
      goal_id: 1,
      kind: 'deposit',
      description: '',
      created_at: '2026-10-24T20:00:00Z',
      lines: [],
    }
  if (url.includes('/balance')) {
    return {
      goal_id: 1,
      total_cents: 0,
      contributed_cents: 0,
      fees_cents: 0,
      holdings: {},
      weights: {},
    }
  }
  if (url.includes('/entries') || url.includes('/rebalances')) return []
  if (url.includes('/projection')) {
    return {
      goal_id: 1,
      horizon_months: 24,
      start_cents: 0,
      target_cents: GOAL.target_cents,
      simulation: SIMULATION,
    }
  }
  if (url.includes('/glide-path')) {
    return {
      profile: 'dynamic',
      horizon_months: 24,
      points: [0, 1, 2].map((year) => ({
        year,
        months_remaining: 24 - year * 12,
        weights: WEIGHTS,
        equity_share: 0.75,
      })),
    }
  }
  return GOAL
}

function stubApi() {
  const calls: Request[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) => {
      calls.push(request.clone())
      return new Response(JSON.stringify(respond(request.url, request.method)), {
        headers: { 'Content-Type': 'application/json' },
      })
    }),
  )
  return calls
}

afterEach(() => vi.unstubAllGlobals())

test('ledger amounts and milestones', () => {
  const entry = (kind: string, lines: [string, number][]): JournalEntry => ({
    id: 1,
    goal_id: 1,
    kind,
    description: '',
    created_at: '',
    lines: lines.map(([account, amount_cents]) => ({ account, amount_cents })),
  })
  expect(
    entryAmount(
      entry('deposit', [
        ['external_bank', -500],
        ['holding:money_market', 500],
      ]),
    ),
  ).toBe(500)
  expect(
    entryAmount(
      entry('market', [
        ['holding:global_equity', -120],
        ['market', 120],
      ]),
    ),
  ).toBe(-120)
  expect(
    entryAmount(
      entry('rebalance', [
        ['holding:global_equity', -300],
        ['holding:euro_gov_bonds', 300],
      ]),
    ),
  ).toBe(300)
  expect(nextMilestone(0, 100_000)).toBe(25_000)
  expect(nextMilestone(30_000, 100_000)).toBe(50_000)
  expect(nextMilestone(100_000, 100_000)).toBeNull()
})

test('a new goal shows inviting empty states and books a deposit with an idempotency key', async () => {
  mockReducedMotion(true)
  window.localStorage.setItem('cairn.tour.goal', 'seen')
  const calls = stubApi()
  const user = userEvent.setup()
  renderWithProviders(
    <Routes>
      <Route path="/goals/:id" element={<GoalDetailPage />} />
    </Routes>,
    { route: '/goals/1' },
  )

  expect(await screen.findByRole('heading', { name: 'Retirement top-up' })).toBeInTheDocument()
  expect(
    await screen.findByText('No deposits yet. Add your first deposit to start the ledger.'),
  ).toBeInTheDocument()
  expect(screen.getByText(/No rebalances yet/)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Replay 2008' })).toBeInTheDocument()

  await user.type(screen.getByLabelText('Amount (€)'), '250')
  await user.click(screen.getByRole('button', { name: 'Deposit' }))
  await waitFor(() => expect(calls.some((c) => c.url.includes('/deposits'))).toBe(true))
  const deposit = calls.find((c) => c.url.includes('/deposits'))!
  expect(deposit.headers.get('Idempotency-Key')).toBeTruthy()
  expect(await deposit.json()).toEqual({ amount_cents: 25_000 })
})

test('the goals page invites you to plan a first goal when there are none', async () => {
  stubApi()
  renderWithProviders(<GoalsPage />)
  expect(await screen.findByText(/No goals yet/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Plan a new goal' })).toHaveAttribute('href', '/start')
})

test('the solver suggests options and "Use this plan" updates the goal', async () => {
  mockReducedMotion(true)
  window.localStorage.setItem('cairn.tour.goal', 'seen')
  const calls = stubApi()
  const user = userEvent.setup()
  renderWithProviders(
    <Routes>
      <Route path="/goals/:id" element={<GoalDetailPage />} />
    </Routes>,
    { route: '/goals/1' },
  )

  await user.click(await screen.findByRole('button', { name: 'How do I get there?' }))
  expect(await screen.findByText('Push the date to April 2039')).toBeInTheDocument()
  expect(screen.getByText('Save €6,000 a month')).toBeInTheDocument()
  expect(screen.getByText('Aim for €9,000')).toBeInTheDocument()
  expect(calls.some((c) => c.method === 'POST' && c.url.endsWith('/goals/1/solve'))).toBe(true)

  await user.click(
    screen.getByRole('button', { name: 'Use this plan: Push the date to April 2039' }),
  )
  await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
  const patch = calls.find((c) => c.method === 'PATCH')!
  expect(patch.url).toMatch(/[/]goals[/]1$/)
  expect(await patch.json()).toEqual({ target_date: '2039-04-25' })
})
