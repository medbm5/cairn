// TanStack Query hooks, one group per API resource.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap, type Schemas } from './api'
import type { Language } from './i18n'

export type Goal = Schemas['GoalOut']
export type GoalCreate = Schemas['GoalCreate']
export type Profile = Schemas['ProfileOut']
export type RiskProfile = Schemas['RiskProfile']
export type SimulationRequest = Schemas['SimulationRequest']
export type Simulation = Schemas['SimulationResponse']
export type GlidePath = Schemas['GlidePathResponse']
export type Balance = Schemas['BalanceOut']
export type JournalEntry = Schemas['JournalEntryOut']
export type Rebalance = Schemas['RebalanceOut']
export type StressTest = Schemas['StressTestOut']
export type Scenario = Schemas['Scenario']
export type ExplainRequest = Schemas['ExplainRequest']
export type Explanation = Schemas['Explanation']
export type Question = Schemas['QuestionOut']

// --- Profiles and questionnaire ---

export function useProfiles() {
  return useQuery({
    queryKey: ['profiles'],
    queryFn: async () => unwrap(await api.GET('/profiles')),
    staleTime: Infinity,
  })
}

export function useQuestionnaire(language: Language) {
  return useQuery({
    queryKey: ['questionnaire', language],
    queryFn: async () =>
      unwrap(await api.GET('/questionnaire', { params: { query: { language } } })),
    staleTime: Infinity,
  })
}

export function useScoreQuestionnaire() {
  return useMutation({
    mutationFn: async (answers: Record<string, string>) =>
      unwrap(await api.POST('/questionnaire/score', { body: { answers } })),
  })
}

// --- Simulation and glide path ---

export function useSimulation(request: SimulationRequest | null) {
  return useQuery({
    queryKey: ['simulation', request],
    queryFn: async () => unwrap(await api.POST('/simulations', { body: request! })),
    enabled: request !== null,
    // Keep the previous drawing on screen while the next one loads, so it never flashes.
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
  })
}

export function useGlidePath(profile: RiskProfile | undefined, horizonMonths: number | undefined) {
  return useQuery({
    queryKey: ['glide-path', profile, horizonMonths],
    queryFn: async () =>
      unwrap(
        await api.GET('/glide-path', {
          params: { query: { profile: profile!, horizon_months: horizonMonths! } },
        }),
      ),
    enabled: profile !== undefined && horizonMonths !== undefined && horizonMonths >= 12,
    staleTime: Infinity,
  })
}

// --- Goals ---

export function useGoals() {
  return useQuery({
    queryKey: ['goals'],
    queryFn: async () => unwrap(await api.GET('/goals')),
  })
}

export function useGoal(goalId: number) {
  return useQuery({
    queryKey: ['goals', goalId],
    queryFn: async () =>
      unwrap(await api.GET('/goals/{goal_id}', { params: { path: { goal_id: goalId } } })),
  })
}

export function useCreateGoal() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async (body: GoalCreate) => unwrap(await api.POST('/goals', { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: ['goals'] }),
  })
}

export function useProjection(goalId: number) {
  return useQuery({
    queryKey: ['goals', goalId, 'projection'],
    queryFn: async () =>
      unwrap(
        await api.GET('/goals/{goal_id}/projection', {
          params: { path: { goal_id: goalId }, query: { paths: 2000 } },
        }),
      ),
  })
}

// --- Ledger ---

export function useBalance(goalId: number) {
  return useQuery({
    queryKey: ['goals', goalId, 'balance'],
    queryFn: async () =>
      unwrap(await api.GET('/goals/{goal_id}/balance', { params: { path: { goal_id: goalId } } })),
  })
}

export function useEntries(goalId: number) {
  return useQuery({
    queryKey: ['goals', goalId, 'entries'],
    queryFn: async () =>
      unwrap(await api.GET('/goals/{goal_id}/entries', { params: { path: { goal_id: goalId } } })),
  })
}

export function useRebalances(goalId: number) {
  return useQuery({
    queryKey: ['goals', goalId, 'rebalances'],
    queryFn: async () =>
      unwrap(
        await api.GET('/goals/{goal_id}/rebalances', { params: { path: { goal_id: goalId } } }),
      ),
  })
}

export function useDeposit(goalId: number) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: async ({ amountCents, key }: { amountCents: number; key: string }) =>
      unwrap(
        await api.POST('/goals/{goal_id}/deposits', {
          params: { path: { goal_id: goalId }, header: { 'Idempotency-Key': key } },
          body: { amount_cents: amountCents },
        }),
      ),
    onSuccess: () => client.invalidateQueries({ queryKey: ['goals', goalId] }),
  })
}

export function useStressTest(goalId: number) {
  return useMutation({
    mutationFn: async (scenario: Scenario) =>
      unwrap(
        await api.POST('/goals/{goal_id}/stress-tests/{scenario}', {
          params: { path: { goal_id: goalId, scenario } },
        }),
      ),
  })
}

// --- Explanations ---

export async function fetchExplanation(request: ExplainRequest): Promise<Explanation> {
  return unwrap(await api.POST('/explain', { body: request }))
}
