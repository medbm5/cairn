import { blendWeights } from './assets'

test('the time machine blends the allocation between two years', () => {
  const now = { global_equity: 0.8, emerging_equity: 0.1, euro_gov_bonds: 0.1, money_market: 0 }
  const next = { global_equity: 0.6, emerging_equity: 0.1, euro_gov_bonds: 0.2, money_market: 0.1 }
  expect(blendWeights(now, next, 0)).toEqual(now)
  const half = blendWeights(now, next, 0.5)
  expect(half.global_equity).toBeCloseTo(0.7)
  expect(half.money_market).toBeCloseTo(0.05)
  expect(Object.values(half).reduce((sum, w) => sum + (w ?? 0), 0)).toBeCloseTo(1)
})
