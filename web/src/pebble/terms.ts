import type { Language } from '../lib/i18n'

// Display names of the API glossary keys (api/src/cairn/explain/glossary.py), so tapped terms
// can be labelled without an extra request.
export const TERM_NAMES: Record<string, Record<Language, string>> = {
  volatility: { en: 'volatility', fr: 'volatilité' },
  diversification: { en: 'diversification', fr: 'diversification' },
  etf: { en: 'ETF', fr: 'ETF' },
  equity: { en: 'shares', fr: 'actions' },
  emerging_markets: { en: 'emerging markets', fr: 'marchés émergents' },
  bond: { en: 'bond', fr: 'obligation' },
  money_market: { en: 'money market', fr: 'monétaire' },
  asset_class: { en: 'asset class', fr: "classe d'actifs" },
  allocation: { en: 'allocation', fr: 'allocation' },
  risk_profile: { en: 'risk profile', fr: 'profil de risque' },
  time_horizon: { en: 'time horizon', fr: 'horizon de placement' },
  compound_growth: { en: 'compound growth', fr: 'intérêts composés' },
  inflation: { en: 'inflation', fr: 'inflation' },
  percentile: { en: 'percentile', fr: 'percentile' },
  median: { en: 'median', fr: 'médiane' },
  monte_carlo: { en: 'simulation', fr: 'simulation' },
  success_probability: { en: 'chance of reaching the goal', fr: "chance d'atteindre l'objectif" },
  glide_path: { en: 'glide path', fr: 'trajectoire de sécurisation' },
  rebalancing: { en: 'rebalancing', fr: 'rééquilibrage' },
  drift: { en: 'drift', fr: 'dérive' },
  drawdown: { en: 'drawdown', fr: 'baisse maximale' },
  recovery: { en: 'recovery', fr: 'reprise' },
  interest_rates: { en: 'interest rates', fr: "taux d'intérêt" },
  ledger: { en: 'ledger', fr: 'grand livre' },
  double_entry: { en: 'double-entry', fr: 'partie double' },
  fees: { en: 'fees', fr: 'frais' },
}

export function termName(key: string, language: Language): string {
  return TERM_NAMES[key]?.[language] ?? key.replace(/_/g, ' ')
}
