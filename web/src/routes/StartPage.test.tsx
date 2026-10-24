import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'
import { mockReducedMotion, renderWithProviders } from '../test/utils'
import { StartPage } from './StartPage'

const QUESTIONS = [
  {
    id: 'horizon',
    text: 'When will you need this money?',
    options: [
      { id: 'lt3', text: 'In less than 3 years' },
      { id: 'gt20', text: 'In more than 20 years' },
    ],
  },
  {
    id: 'drop_reaction',
    text: 'Your investments fall by 20%. What do you do?',
    options: [
      { id: 'sell_all', text: 'Sell everything' },
      { id: 'wait', text: 'Wait it out' },
    ],
  },
]
const PROFILE = {
  key: 'dynamic',
  name: 'Dynamic',
  description: '',
  equity_share: 0.75,
  weights: { global_equity: 0.6, emerging_equity: 0.15, euro_gov_bonds: 0.2, money_market: 0.05 },
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => vi.unstubAllGlobals())

test('onboarding creates the goal from the form, answers and profile', async () => {
  mockReducedMotion(true)
  const requests: { url: string; method: string; body: string }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: Request) => {
      const body = input.method === 'GET' ? '' : await input.clone().text()
      requests.push({ url: input.url, method: input.method, body })
      if (input.url.includes('/questionnaire/score')) {
        return json({ score: 18, max_score: 24, profile: PROFILE })
      }
      if (input.url.includes('/questionnaire')) return json(QUESTIONS)
      if (input.url.endsWith('/goals')) return json({ id: 7 }, 201)
      return json({})
    }),
  )
  const user = userEvent.setup()
  renderWithProviders(<StartPage />)

  // Step 1: validation first, then a valid goal.
  await user.click(screen.getByRole('button', { name: 'Continue' }))
  expect(screen.getByText('Choose what you are saving for.')).toBeInTheDocument()

  await user.click(screen.getByLabelText('A home'))
  await user.type(screen.getByLabelText('Name your goal'), 'A flat in Lyon')
  await user.type(screen.getByLabelText('How much do you need? (€)'), '60 000')
  const year = new Date().getFullYear() + 8
  await user.click(screen.getByRole('button', { name: /^When do you need it\?/ }))
  await user.selectOptions(screen.getByLabelText('Year'), String(year))
  await user.click(screen.getByRole('button', { name: `June ${year}` }))
  await user.type(screen.getByLabelText('How much can you put aside each month? (€)'), '400')
  await user.click(screen.getByRole('button', { name: 'Continue' }))

  // Step 2: one question per screen; the horizon comes from the goal date, so it is not asked.
  expect(
    await screen.findByText('Your investments fall by 20%. What do you do?'),
  ).toBeInTheDocument()
  expect(screen.queryByText('When will you need this money?')).not.toBeInTheDocument()
  await user.click(await screen.findByLabelText('Wait it out'))
  await user.click(screen.getByRole('button', { name: 'Continue' }))

  // Step 3: the profile, then the goal is created.
  expect(await screen.findByRole('heading', { name: 'Your profile: Dynamic' })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'See my projection' }))

  await waitFor(() => expect(requests.some((r) => r.url.endsWith('/goals'))).toBe(true))
  const created = JSON.parse(requests.find((r) => r.url.endsWith('/goals'))!.body)
  expect(created).toMatchObject({
    name: 'A flat in Lyon',
    type: 'home',
    target_cents: 6_000_000,
    monthly_contribution_cents: 40_000,
    profile: 'dynamic',
  })
  expect(created.target_date.startsWith(`${year}-06-`)).toBe(true)
  const scored = JSON.parse(requests.find((r) => r.url.includes('/score'))!.body)
  // June, eight years ahead: 90 to 101 months away whatever today's month, so "5 to 10 years".
  expect(scored.answers).toEqual({ horizon: '5to10', drop_reaction: 'wait' })
})
