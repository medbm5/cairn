import { useQuery } from '@tanstack/react-query'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { API_URL } from '../lib/api'
import { useLanguage } from '../lib/i18n'
import { fetchExplanation, type ExplainRequest, type Explanation } from '../lib/queries'
import { readStorage, writeStorage } from '../lib/storage'
import type { PebbleState } from './states'

export type Topic = ExplainRequest['topic']
export type Level = 'simple' | 'more_detail'

/** What Pebble can be asked to say. */
export type SayRequest =
  | {
      topic: Exclude<Topic, 'term'>
      facts: Record<string, unknown>
      anchorId?: string
      level?: Level
    }
  | { term: string; anchorId?: string }
  | { text: string; title?: string; anchorId?: string }

export interface Message {
  id: number
  request: SayRequest
}

export interface TourStep {
  anchorId: string
  title?: string
  text: string
}

interface PebbleContextValue {
  /** Queue an explanation; messages are shown one at a time, in order. */
  say: (request: SayRequest) => void
  pointAt: (anchorId: string | null) => void
  setState: (state: PebbleState) => void
  tour: (steps: TourStep[]) => void
  dismiss: () => void
  tellMeMore: () => void
  explainTerm: (term: string) => void
  state: PebbleState
  target: string | null
  current: Message | null
  queueLength: number
  explanation: Explanation | undefined
  explanationLoading: boolean
  explanationError: boolean
  statusLine: string | null
  waking: boolean
  quiet: boolean
  setQuiet: (quiet: boolean) => void
  registerAnchor: (id: string, element: HTMLElement | null) => void
  getAnchor: (id: string) => HTMLElement | undefined
  hasAnchor: (id: string) => boolean
  registerSlot: (id: string, present: boolean) => void
  hasSlot: (id: string) => boolean
}

const PebbleContext = createContext<PebbleContextValue | null>(null)

const QUIET_KEY = 'cairn.quietPebble'
const COLD_START_MS = 2000

type ExplainFn = (request: ExplainRequest) => Promise<Explanation>

async function pingHealth(): Promise<void> {
  await fetch(`${API_URL}/health`)
}

function explainRequestFor(request: SayRequest, language: 'en' | 'fr'): ExplainRequest | null {
  if ('text' in request) return null
  if ('term' in request) return { topic: 'term', term: request.term, language, level: 'simple' }
  return { topic: request.topic, facts: request.facts, level: request.level ?? 'simple', language }
}

export function PebbleProvider({
  children,
  explain = fetchExplanation,
  pingApi = pingHealth,
}: {
  children: ReactNode
  explain?: ExplainFn
  pingApi?: () => Promise<void>
}) {
  const { language, t } = useLanguage()
  const [queue, setQueue] = useState<Message[]>([])
  const [baseState, setBaseState] = useState<PebbleState>('idle')
  const [manualTarget, setManualTarget] = useState<string | null>(null)
  const [quiet, setQuietState] = useState(() => readStorage(QUIET_KEY) === 'true')
  const [statusLine, setStatusLine] = useState<string | null>(null)
  const [waking, setWaking] = useState(false)
  const nextId = useRef(1)
  const anchors = useRef(new Map<string, HTMLElement>())
  const slots = useRef(new Set<string>())
  const [, setRegistryVersion] = useState(0)

  const current = queue[0] ?? null
  const request = current ? explainRequestFor(current.request, language) : null
  const query = useQuery({
    queryKey: ['explain', request],
    queryFn: () => explain(request!),
    enabled: request !== null,
    staleTime: Infinity,
    retry: 1,
  })

  // --- Pointing: the current message's anchor wins over a manual pointAt() ---
  const pointAt = useCallback((anchorId: string | null) => setManualTarget(anchorId), [])
  const target = current?.request.anchorId ?? manualTarget

  // --- Queue ---
  const say = useCallback((sayRequest: SayRequest) => {
    setQueue((q) => [...q, { id: nextId.current++, request: sayRequest }])
  }, [])

  const dismiss = useCallback(() => {
    setQueue((q) => q.slice(1))
    setManualTarget(null)
  }, [])

  const replaceCurrent = useCallback((next: SayRequest) => {
    setQueue((q) => [{ id: nextId.current++, request: next }, ...q.slice(1)])
  }, [])

  const tellMeMore = useCallback(() => {
    if (current && 'topic' in current.request) {
      replaceCurrent({ ...current.request, level: 'more_detail' })
    }
  }, [current, replaceCurrent])

  const explainTerm = useCallback(
    (term: string) => replaceCurrent({ term, anchorId: current?.request.anchorId }),
    [current, replaceCurrent],
  )

  const tour = useCallback((steps: TourStep[]) => {
    setQueue(steps.map((step) => ({ id: nextId.current++, request: step })))
  }, [])

  // --- Quiet mode ---
  const setQuiet = useCallback((value: boolean) => {
    setQuietState(value)
    writeStorage(QUIET_KEY, String(value))
  }, [])

  // --- Registries ---
  const registerAnchor = useCallback((id: string, element: HTMLElement | null) => {
    if (element) anchors.current.set(id, element)
    else anchors.current.delete(id)
    setRegistryVersion((v) => v + 1)
  }, [])

  const registerSlot = useCallback((id: string, present: boolean) => {
    if (present) slots.current.add(id)
    else slots.current.delete(id)
    setRegistryVersion((v) => v + 1)
  }, [])

  // --- Cold start: if the API takes over two seconds to answer, Pebble sleeps until it does ---
  useEffect(() => {
    let answered = false
    let wakeTimer = 0
    const sleepTimer = window.setTimeout(() => {
      if (answered) return
      setBaseState('sleep')
      setStatusLine(t('wakingUp'))
    }, COLD_START_MS)
    pingApi()
      .catch(() => undefined)
      .finally(() => {
        answered = true
        window.clearTimeout(sleepTimer)
        setStatusLine((line) => {
          if (line !== null) {
            setBaseState('idle')
            setWaking(true)
            wakeTimer = window.setTimeout(() => setWaking(false), 900)
          }
          return null
        })
      })
    return () => {
      window.clearTimeout(sleepTimer)
      window.clearTimeout(wakeTimer)
    }
    // Run once per page load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // While Pebble moves between anchors, PebbleLayer shows the 'walk' state on top of this one.
  let state: PebbleState = baseState
  if (target) state = 'point'
  if (current) {
    const isText = 'text' in current.request
    state = query.isFetching ? 'think' : isText && target ? 'point' : 'explain'
  }

  const value: PebbleContextValue = {
    say,
    pointAt,
    setState: setBaseState,
    tour,
    dismiss,
    tellMeMore,
    explainTerm,
    state,
    target,
    current,
    queueLength: queue.length,
    explanation: query.data,
    explanationLoading: query.isFetching,
    explanationError: query.isError,
    statusLine,
    waking,
    quiet,
    setQuiet,
    registerAnchor,
    getAnchor: (id) => anchors.current.get(id),
    hasAnchor: (id) => anchors.current.has(id),
    registerSlot,
    hasSlot: (id) => slots.current.has(id),
  }

  return <PebbleContext.Provider value={value}>{children}</PebbleContext.Provider>
}

export function usePebble(): PebbleContextValue {
  const context = useContext(PebbleContext)
  if (!context) throw new Error('usePebble must be used inside PebbleProvider')
  return context
}

/** Register an element Pebble can walk to and point at. Unregisters on unmount. */
export function usePebbleAnchor(id: string): (element: HTMLElement | null) => void {
  const { registerAnchor } = usePebble()
  return useCallback(
    (element: HTMLElement | null) => registerAnchor(id, element),
    [id, registerAnchor],
  )
}

/** Where explanations appear inline when Pebble is quiet. */
export function useInlineSlot(id: string): void {
  const { registerSlot } = usePebble()
  useEffect(() => {
    registerSlot(id, true)
    return () => registerSlot(id, false)
  }, [id, registerSlot])
}
