import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, vi } from 'vitest'
import { renderWithProviders } from '../test/utils'
import { ObservabilityPage } from './ObservabilityPage'

const A = 'a'.repeat(32)
const B = 'b'.repeat(32)

const STATS = {
  since: '2026-10-25T08:00:00Z',
  api: {
    requests: 2,
    status_counts: { '2xx': 2 },
    error_rate: 0,
    p50_ms: 12,
    p95_ms: 480,
    routes: [{ method: 'POST', route: '/explain', count: 2, errors: 0, p50_ms: 12, p95_ms: 480 }],
    recent: [
      {
        at: '2026-10-25T08:01:00Z',
        method: 'POST',
        route: '/explain',
        path: '/explain',
        status: 200,
        duration_ms: 480,
        request_id: A,
      },
      {
        at: '2026-10-25T08:02:00Z',
        method: 'GET',
        route: '/goals',
        path: '/goals',
        status: 200,
        duration_ms: 12,
        request_id: B,
      },
    ],
  },
  llm: {
    model: 'gpt-5-nano',
    enabled: true,
    explanations: 4,
    sources: { ai: 1, cache: 2, fallback: 1 },
    fallback_reasons: { glossary: 1 },
    calls: 1,
    failed_calls: 0,
    input_tokens: 320,
    output_tokens: 90,
    reasoning_tokens: 0,
    cost_usd: 0.000052,
    avg_latency_ms: 450,
    topics: [
      {
        topic: 'projection',
        explanations: 3,
        ai: 1,
        cache: 2,
        fallback: 0,
        calls: 1,
        input_tokens: 320,
        output_tokens: 90,
        cost_usd: 0.000052,
      },
    ],
    recent: [],
  },
  logs: [
    {
      at: '2026-10-25T08:01:00Z',
      level: 'warning',
      event: 'explain.guard_rejected',
      logger: null,
      request_id: A,
      fields: { topic: 'projection' },
    },
    {
      at: '2026-10-25T08:02:00Z',
      level: 'info',
      event: 'request',
      logger: null,
      request_id: B,
      fields: { status: 200 },
    },
  ],
}

afterEach(() => vi.unstubAllGlobals())

test('shows traffic and AI usage, and follows one request through the trail', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(
      async () =>
        new Response(JSON.stringify(STATS), { headers: { 'Content-Type': 'application/json' } }),
    ),
  )
  const user = userEvent.setup()
  renderWithProviders(<ObservabilityPage />)

  expect((await screen.findAllByText('320 / 90')).length).toBeGreaterThan(0)
  expect(screen.getByText('Model: gpt-5-nano')).toBeInTheDocument()
  expect(screen.getByText('glossary term 1')).toBeInTheDocument()
  expect(screen.getByText('explain.guard_rejected')).toBeInTheDocument()
  expect(screen.getByText('request')).toBeInTheDocument()

  // Following request A hides everything that belongs to request B.
  const trail = screen.getByRole('heading', { name: 'Trail' }).closest('section')!
  await user.click(within(trail).getAllByRole('button', { name: 'aaaaaaaa' })[0])
  expect(screen.getByText(/Following request aaaaaaaa/)).toBeInTheDocument()
  expect(screen.getByText('explain.guard_rejected')).toBeInTheDocument()
  expect(screen.queryByText('request')).not.toBeInTheDocument()
  expect(within(trail).queryByText('GET /goals')).not.toBeInTheDocument()
})
