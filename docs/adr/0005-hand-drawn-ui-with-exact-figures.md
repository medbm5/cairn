# 0005 Hand-drawn interface with exact figures

- Status: accepted
- Date: 2026-10-24

## Context

Investing apps often look like trading terminals, which intimidates the people Cairn is for:
first-time savers. We want the feeling of a friendly engineer sketching a plan on paper. But a
sketch must never make money look approximate: an amount drawn in a wobbly hand reads as
"roughly", and a chart that redraws differently on every render looks unreliable.

## Decision

- **The plan is drawn by hand; the numbers are exact.** Charts, arrows, outlines, highlights and
  Pebble are drawn with Rough.js and rough-notation. Every figure (amounts, percentages, dates in
  tables) is set in Atkinson Hyperlegible with tabular numerals, formatted with `Intl` for the
  chosen language.
- **Stable sketches.** Every hand-drawn element uses a fixed seed derived from a stable id, so
  lines look hand-drawn but do not wobble between renders.
- **Ink means likelihood.** The projection's P10–P90 range is hatching, denser in the P25–P75
  band, so likelier outcomes literally carry more ink. The median is a confident pen line, the
  target a dashed line ending in a small cairn.
- **Fast while moving, sketched when still.** While a slider moves, bands render as smooth SVG
  paths; about 150 ms after the last change they are re-sketched with Rough.js.
- **Drawings never carry information alone.** Each chart has a text summary for screen readers,
  allocations have an exact legend, stress tests end with a sentence, and textures (hatching,
  cross-hatching, dots) distinguish asset classes without relying on colour.
- **Motion is optional.** With `prefers-reduced-motion`, lines appear complete, there is no smooth
  scrolling and Pebble changes pose without moving.
- **Two themes from one palette.** A notebook page (light) and a blueprint (dark), both defined
  as CSS variables, with text contrast checked against AA.

## Consequences

- Rough.js work costs main-thread time. The landing hero is sketched in idle time after first
  paint and below-the-fold drawings load lazily; the production build scores 93 for mobile
  performance and 100 for accessibility in Lighthouse.
- Hand-drawn primitives are custom components (`SketchBox`, `SketchButton`, `SketchArrow`, …),
  measured with `ResizeObserver` so outlines fit their content.
- Primary buttons use a solid highlighter fill with dark ink in both themes, because hatching
  behind text hurt legibility on the blueprint theme.
