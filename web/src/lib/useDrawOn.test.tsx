import { renderHook } from '@testing-library/react'
import { afterEach } from 'vitest'
import { mockReducedMotion } from '../test/utils'
import { useDrawOn } from './useDrawOn'

afterEach(() => mockReducedMotion(false))

test('returns the finished state immediately under reduced motion', () => {
  mockReducedMotion(true)
  const { result } = renderHook(() => useDrawOn({ duration: 5000 }))
  expect(result.current.done).toBe(true)
  expect(result.current.pathProps).toEqual({})
})

test('starts hidden and animates when motion is allowed', () => {
  mockReducedMotion(false)
  const { result } = renderHook(() => useDrawOn({ duration: 5000 }))
  expect(result.current.done).toBe(false)
  expect(result.current.pathProps.pathLength).toBe(1)
  expect(result.current.pathProps.style?.strokeDashoffset).toBe(1)
})
