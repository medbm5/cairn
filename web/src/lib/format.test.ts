import { formatDuration, formatMoney, formatPercent } from './format'

// Intl uses (narrow) no-break spaces in French; normalise all whitespace to plain spaces.
const plain = (text: string) => text.replace(/\s/g, ' ')

test('formats cents as whole euros in each language', () => {
  expect(plain(formatMoney(1_200_000, 'fr'))).toBe('12 000 €')
  expect(formatMoney(1_200_000, 'en')).toBe('€12,000')
})

test('can show cents when asked', () => {
  expect(formatMoney(123_456, 'en', 2)).toBe('€1,234.56')
  expect(plain(formatMoney(123_456, 'fr', 2))).toBe('1 234,56 €')
})

test('formats fractions as percentages', () => {
  expect(formatPercent(0.758, 'en')).toBe('76%')
  expect(plain(formatPercent(0.758, 'fr'))).toBe('76 %')
  expect(formatPercent(0.0725, 'en', 1)).toBe('7.3%')
})

test('formats durations in years and months', () => {
  expect(formatDuration(24, 'en')).toBe('2 years')
  expect(formatDuration(13, 'fr')).toBe('1 an et 1 mois')
  expect(formatDuration(5, 'en')).toBe('5 months')
})
