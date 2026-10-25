import type { Solution, SolverOption } from '../../lib/queries'

/** The facts Pebble's "solver" explanation is built from, all taken from the solver's answer. */
export function solverFacts(solution: Solution): Record<string, unknown> {
  const by = Object.fromEntries(solution.options.map((o) => [o.lever, o])) as Record<
    SolverOption['lever'],
    SolverOption
  >
  const { contribution, horizon, target } = by
  // Read 'YYYY-MM-DD' as written: new Date() would read it as UTC midnight and could shift the
  // month west of Greenwich.
  const [year, month] = (horizon.target_date ?? new Date().toISOString()).split('-').map(Number)
  return {
    target_cents: target.current,
    monthly_contribution_cents: contribution.current,
    horizon_months: horizon.current,
    current_probability: solution.current_probability,
    target_probability: solution.target_probability,
    needed_monthly_contribution_cents: contribution.value,
    contribution_increase_cents: contribution.delta,
    contribution_feasible: contribution.feasible,
    probability_with_contribution: contribution.success_probability,
    needed_horizon_months: horizon.value,
    horizon_extension_months: horizon.delta,
    needed_goal_year: year,
    needed_goal_month: month,
    horizon_feasible: horizon.feasible,
    probability_with_horizon: horizon.success_probability,
    reachable_target_cents: target.value,
    target_reduction_cents: -target.delta,
    target_feasible: target.feasible,
    probability_with_target: target.success_probability,
  }
}
