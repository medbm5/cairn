export const PEBBLE_STATES = [
  'idle',
  'walk',
  'point',
  'sketch',
  'explain',
  'think',
  'sleep',
  'cheer',
  'worried',
] as const

export type PebbleState = (typeof PEBBLE_STATES)[number]
