export const ASSET_ORDER = [
  'global_equity',
  'emerging_equity',
  'euro_gov_bonds',
  'money_market',
] as const
export type AssetClass = (typeof ASSET_ORDER)[number]
export type Weights = Partial<Record<AssetClass, number>>
