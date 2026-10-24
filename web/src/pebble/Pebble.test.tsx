import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { renderWithProviders } from '../test/utils'
import { PebbleInline } from './PebbleInline'
import { PebbleLayer } from './PebbleLayer'
import { usePebble, usePebbleAnchor } from './PebbleProvider'

function Speaker() {
  const pebble = usePebble()
  return (
    <>
      <button onClick={() => pebble.say({ text: 'First message' })}>say first</button>
      <button onClick={() => pebble.say({ text: 'Second message' })}>say second</button>
      <button
        onClick={() =>
          pebble.say({
            topic: 'projection',
            facts: { profile: 'balanced' },
            anchorId: 'chart',
          })
        }
      >
        explain chart
      </button>
      <button onClick={() => pebble.setQuiet(true)}>quiet</button>
      <p data-testid="queue">{pebble.queueLength}</p>
      <p data-testid="state">{pebble.state}</p>
    </>
  )
}

test('provider queues messages and shows them in order', async () => {
  const user = userEvent.setup()
  renderWithProviders(
    <>
      <Speaker />
      <PebbleLayer />
    </>,
  )
  await user.click(screen.getByText('say first'))
  await user.click(screen.getByText('say second'))
  expect(screen.getByTestId('queue')).toHaveTextContent('2')
  expect(await screen.findByText('First message')).toBeInTheDocument()
  expect(screen.queryByText('Second message')).not.toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: 'Next' }))
  expect(await screen.findByText('Second message')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Got it' }))
  expect(screen.getByTestId('queue')).toHaveTextContent('0')
})

test('explanations come from /explain and "Tell me more" asks for more detail', async () => {
  const user = userEvent.setup()
  renderWithProviders(
    <>
      <Speaker />
      <PebbleLayer />
    </>,
  )
  await user.click(screen.getByText('explain chart'))
  expect(await screen.findByText('Plain words about projection (simple).')).toBeInTheDocument()
  expect(screen.getByTestId('state')).toHaveTextContent(/explain|point/)

  await user.click(screen.getByRole('button', { name: 'Tell me more' }))
  expect(await screen.findByText('Plain words about projection (more_detail).')).toBeInTheDocument()
})

test('quiet mode renders explanations inline, without the robot', async () => {
  const user = userEvent.setup()
  renderWithProviders(
    <>
      <Speaker />
      <section data-testid="chart-section">
        <PebbleInline anchorId="chart" />
      </section>
      <PebbleLayer />
    </>,
  )
  await user.click(screen.getByText('quiet'))
  await user.click(screen.getByText('explain chart'))

  const section = screen.getByTestId('chart-section')
  await waitFor(() => expect(section).toHaveTextContent('Plain words about projection (simple).'))
  expect(screen.queryByRole('img', { name: /Pebble/ })).not.toBeInTheDocument()
})

function Anchored() {
  const ref = usePebbleAnchor('target')
  return <div ref={ref}>target</div>
}

function AnchorHarness() {
  const [mounted, setMounted] = useState(true)
  const pebble = usePebble()
  return (
    <>
      {mounted && <Anchored />}
      <button onClick={() => setMounted(false)}>unmount</button>
      <p data-testid="has-anchor">{String(pebble.hasAnchor('target'))}</p>
    </>
  )
}

test('anchors register on mount and unregister on unmount', async () => {
  const user = userEvent.setup()
  renderWithProviders(<AnchorHarness />)
  expect(screen.getByTestId('has-anchor')).toHaveTextContent('true')
  await act(() => user.click(screen.getByText('unmount')))
  expect(screen.getByTestId('has-anchor')).toHaveTextContent('false')
})
