import { horizonAnswer, monthsUntil, parseEuros, targetDate, validateGoal } from './goalForm'

test('parses euro amounts typed in English or French style', () => {
  expect(parseEuros('12000')).toBe(1_200_000)
  expect(parseEuros('12 000')).toBe(1_200_000)
  expect(parseEuros('12,000.50')).toBe(1_200_050)
  expect(parseEuros('1.234,5')).toBe(123_450)
  expect(parseEuros('300,25 €')).toBe(30_025)
  expect(parseEuros('')).toBeNull()
  expect(parseEuros('abc')).toBeNull()
  expect(parseEuros('-5')).toBeNull()
})

test('dates are whole months from today', () => {
  const today = new Date(2026, 9, 24) // 24 October 2026
  expect(monthsUntil('2027-10', today)).toBe(12)
  expect(targetDate('2027-10', today)).toBe('2027-10-24')
  expect(targetDate('2027-10', new Date(2026, 0, 31))).toBe('2027-10-28')
})

test('validates every field with a clear message key', () => {
  const today = new Date(2026, 9, 24)
  expect(
    validateGoal({ type: null, name: ' ', target: '0', date: '2026-12', monthly: 'x' }, today),
  ).toEqual({
    type: 'errorType',
    name: 'errorName',
    target: 'errorTarget',
    date: 'errorDate',
    monthly: 'errorMonthly',
  })
  expect(
    validateGoal(
      { type: 'home', name: 'Flat', target: '60 000', date: '2034-06', monthly: '400' },
      today,
    ),
  ).toEqual({})
})

test('the goal date answers the horizon question', () => {
  expect(horizonAnswer(12)).toBe('lt3')
  expect(horizonAnswer(36)).toBe('3to5')
  expect(horizonAnswer(119)).toBe('5to10')
  expect(horizonAnswer(120)).toBe('10to20')
  expect(horizonAnswer(240)).toBe('gt20')
})
