# How AI was used to build Cairn

Cairn was built with **Claude Code** from a single specification, [`BUILD_PLAN.md`](../BUILD_PLAN.md):
twenty slices, each one commit, each committed only after its checks passed (ruff, ruff format,
mypy strict and pytest for the API; ESLint, `tsc`, Vitest and a production build for the web app).

This page records what that looked like in practice: where the first output was wrong or was
rewritten, and how correctness was checked.

## How the work was organised

- **Small slices, green before commit.** Each slice added a feature and its tests together. A
  slice whose checks failed was fixed before committing, never committed red.
- **Deterministic core, explained edges.** The simulation, glide path, ledger, rebalancing and
  stress tests are plain Python covered by unit and property-based tests. The language model is
  only used at runtime to rephrase facts the engine computed, behind a number guard
  ([ADR 0003](adr/0003-llm-boundaries.md)).
- **Library versions over memory.** Where a library had changed since the plan was written, the
  installed version's API was inspected and followed, and the deviation was noted in the commit
  body (for example: the Vite template ships oxlint and no `strict` flag; Tailwind CSS 4 is
  configured in CSS; the OpenAI SDK's structured outputs use `responses.parse`; TypeScript is
  pinned to 5.9 for `openapi-typescript`).

## Where the first output was wrong, and what changed

| Problem | How it was caught | Fix |
|---|---|---|
| Running the seed script twice added two extra rebalances: on the second run, the drift check used today's holdings instead of the historical ones. | A test asserting "safe to run twice" failed. | Months already replayed are skipped as a whole. |
| Sketched outlines were smaller than their boxes. `ResizeObserver`'s `contentRect` excludes padding. | Screenshot of the landing page. | Measure the border box. |
| A test stub for `fetch` was ignored: `openapi-fetch` captures `fetch` when the client is created. | An onboarding test could not find the questionnaire. | The client looks `fetch` up on every call. |
| Mobile Lighthouse performance was 59: render-blocking fonts and a one-second start-up task from sketching every drawing at once. | Lighthouse on the production build. | Non-blocking fonts, lazy animation features, idle-time hero sketch, code-split sections: 93 performance, 100 accessibility. |
| Pebble stood on top of the intro text when pointing at a wide chart. | Screenshot. | Pebble stands inside wide targets, in their empty bottom-right corner. |
| Primary buttons on the dark blueprint theme had white text over yellow hatching. | Screenshot. | Solid highlighter fill with dark ink in both themes. |
| Rebalance explanations needed the drift that triggered them, which is not stored. | Building the rebalance list. | The fact is optional and the template words it without a figure, rather than inventing or parsing one. |
| React's newer hook rules rejected `setState` calls inside effects in several components. | ESLint. | State is derived during render, or set from timers and callbacks. |
| Unicode no-break spaces typed into regular expressions broke lint. | ruff and ESLint. | Escaped code points (` `), or `\s`. |

Some apparent bugs were not bugs: in headless Chrome with virtual time, CSS transitions did not
advance, so self-drawing lines looked missing. Screenshots with reduced motion forced, and a
scripted browser that waited for the page, confirmed the lines were drawn.

## How correctness was checked

- **Property-based tests (Hypothesis)** for the invariants that matter most: questionnaire scoring
  is monotonic; percentiles are ordered; a higher contribution never lowers the chance of
  success; equity never rises along the glide path; cent splits always sum exactly; random
  sequences of deposits and fees always reconcile; rebalancing transfers balance and land within
  one cent of target.
- **Known-answer tests**: zero volatility reproduces compound interest; a 100% equity portfolio
  falls 55% in the stylised 2008 replay; the same seed gives the same projection.
- **The number guard is itself tested**, and every template in both languages is run through it,
  so the fallbacks obey the rule they enforce.
- **Database tests** run on SQLite locally and on PostgreSQL 16 in CI (and were run against
  Postgres locally); Alembic migrations are applied and rolled back in CI.
- **The UI was looked at**: screenshots of every screen in both themes, a scripted check that no
  screen overflows horizontally at 360 px, a scripted 2008 replay, and Lighthouse on the
  production build.

## Human review

AI-written code still needs a person to own it. Before relying on this project, the author should
review at least `api/src/cairn/services/ledger.py`, `api/src/cairn/domain/money.py`,
`api/src/cairn/domain/rebalancing.py` and `api/src/cairn/explain/guard.py` line by line, and
record that review here.
