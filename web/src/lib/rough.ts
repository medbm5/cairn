import rough from 'roughjs'
import type { Drawable, Options, PathInfo } from 'roughjs/bin/core'
import type { RoughGenerator } from 'roughjs/bin/generator'

export type { Options as RoughOptions, PathInfo }

const generator: RoughGenerator = rough.generator()

/** Pen defaults: currentColor strokes so every sketch follows the theme's ink. */
export const PEN: Options = {
  stroke: 'currentColor',
  strokeWidth: 1.6,
  roughness: 1.1,
  bowing: 1,
  fill: undefined,
}

/** A stable rough.js seed from a string id, so a drawing never wobbles between renders. */
export function seedFrom(id: string): number {
  let hash = 2166136261
  for (let i = 0; i < id.length; i++) {
    hash ^= id.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return (Math.abs(hash) % 2_000_000_000) + 1
}

/** Run a rough.js drawing and return plain SVG path data that React can render. */
export function sketch(draw: (g: RoughGenerator) => Drawable): PathInfo[] {
  return generator.toPaths(draw(generator))
}
