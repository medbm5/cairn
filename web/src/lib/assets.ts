export const ASSET_ORDER = [
  'global_equity',
  'emerging_equity',
  'euro_gov_bonds',
  'money_market',
] as const
export type AssetClass = (typeof ASSET_ORDER)[number]
export type Weights = Partial<Record<AssetClass, number>>

/** The allocation part of the way between two yearly glide-path points. */
export function blendWeights(from: Weights, to: Weights, share: number): Weights {
  return Object.fromEntries(
    ASSET_ORDER.map((asset) => [
      asset,
      (from[asset] ?? 0) + ((to[asset] ?? 0) - (from[asset] ?? 0)) * share,
    ]),
  )
}
