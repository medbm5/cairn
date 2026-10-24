import { useEffect, useState } from 'react'

/** True when `value` has not changed for `delay` ms (e.g. a slider was released). */
export function useSettled<T>(value: T, delay = 150): boolean {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(value), delay)
    return () => window.clearTimeout(timer)
  }, [value, delay])
  return Object.is(settled, value)
}

/** The value, updated only once it has stopped changing for `delay` ms. */
export function useDebounced<T>(value: T, delay = 150): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(timer)
  }, [value, delay])
  return debounced
}
