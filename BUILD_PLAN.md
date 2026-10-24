# Cairn — Build plan for Claude Code

Cairn is a goal-based investing demo. A person sets a life goal (retirement, a flat, a safety net), gets a risk profile, sees a live projection of where their savings could land, and watches the portfolio become safer as the goal approaches. Pebble, a small hand-drawn robot, guides them and explains every finance idea in everyday words.

This file is the single source of truth for building the project. Execute the slices **in order**, one commit per slice.

---

## How to run this file

From the empty repository root, start Claude Code and send:

> Read BUILD_PLAN.md and execute every slice in order, following the Rules section. Commit after each slice with its exact commit message. Stop and report if a slice's checks cannot pass.

---

## Rules (apply to every slice)

1. **One slice = one commit.** Use the commit message given in the slice, exactly. Do not squash slices or split them.
2. **Green before commit.** Run the slice's checks and commit only when they pass. Backend: `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest`. Frontend: `npm run lint && npm run typecheck && npm run test && npm run build`.
3. **Keep it simple.** No CQRS, no message queue, no microservices, no abstract base classes "for later". A reviewer should understand any module in under five minutes.
4. **Numbers come from code, never from the LLM.** The OpenAI integration is an explainability layer: it receives facts the deterministic engine already computed and rewrites them in plain language. It never calculates, predicts or recommends.
5. **No secrets in git.** Only `.env.example` files are committed. Every external service (Sentry, OpenAI) must degrade gracefully when its key is missing.
6. **Money is integer cents** in storage and in the ledger. Floats are allowed only inside the simulation engine.
7. **Type everything.** Python: full type hints, `mypy --strict` on `src`. TypeScript: `strict: true`.
8. **Tests ship with the feature**, in the same slice.
9. If a library API differs from what is written here, follow the library's current documentation and note the deviation in the commit body.

---

## Target stack

| Layer | Choice |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL 16 |
| Numerics | NumPy |
| Tooling | uv, ruff, mypy, pytest, Hypothesis |
| Monitoring | Sentry (API + web), structured JSON logs (structlog), request IDs |
| GenAI | Official `openai` Python SDK, structured outputs into Pydantic models |
| Web | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Framer Motion, Lenis |
| Hand-drawn rendering | Rough.js (sketchy shapes and charts), rough-notation (hand-drawn highlights), d3-scale and d3-shape (chart maths) |
| Analytics | Metabase (local, via Docker Compose) |
| Infra | Docker, Docker Compose, Kubernetes manifests (optional), GitHub Actions |
| Hosting | Vercel (web), Render (API + Postgres) |

## Repository layout

```
cairn/
├── api/
│   ├── pyproject.toml
│   ├── alembic/
│   ├── src/cairn/
│   │   ├── main.py            # app factory, middleware, routers
│   │   ├── config.py          # pydantic-settings
│   │   ├── logging.py
│   │   ├── db.py              # engine, session dependency
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── domain/            # pure functions, no I/O
│   │   │   ├── profiles.py
│   │   │   ├── simulation.py
│   │   │   ├── glide_path.py
│   │   │   ├── rebalancing.py
│   │   │   └── stress.py
│   │   ├── services/          # orchestrate domain + DB
│   │   │   ├── goals.py
│   │   │   └── ledger.py
│   │   ├── explain/           # explainability layer: facts, glossary, OpenAI client, fallbacks
│   │   └── routers/           # thin HTTP layer
│   └── tests/
├── web/
│   └── src/ (app, routes, components, pebble, charts, features, lib, styles)
├── infra/
│   ├── docker-compose.yml
│   └── k8s/
├── docs/adr/
├── render.yaml
├── .github/workflows/ci.yml
├── BUILD_PLAN.md
└── README.md
```

---

## Design direction (web)

Follow this precisely; it is what makes the demo memorable.

**Concept: the planning notebook.** Cairn feels like sitting with a friendly engineer who sketches your plan on paper while explaining it. Light mode is a notebook page with a faint blue grid; dark mode is a real blueprint, deep blue with chalk-white lines. Charts, arrows, highlights and the mascot are drawn by hand. The app's figures and body text stay crisp and perfectly legible, because the plan is drawn by hand but the numbers are exact.

**Palette (CSS variables).**

| Token | Light (notebook) | Dark (blueprint) | Use |
|---|---|---|---|
| `--paper` | `#FBFCFD` | `#16365A` | page background |
| `--grid` | `#D6E4F0` | `#25507E` | background grid lines (24 px cells, every 5th line slightly stronger) |
| `--ink` | `#1D3A6B` | `#EEF4FA` | pen lines, headings, primary text |
| `--graphite` | `#5E6670` | `#A9BCD0` | secondary text, axes, construction lines |
| `--highlighter` | `#FFE45C` | `#F6D743` | rough-notation highlights on key terms and the success probability |
| `--red-pen` | `#D2413A` | `#FF7A70` | stress-test drawdowns and warnings only |
| `--leaf` | `#3F8F5A` | `#7FD39A` | goal reached, positive states |

**Type.**
- Architects Daughter: headings, annotations, Pebble's speech bubbles, hand-written labels on charts.
- Atkinson Hyperlegible: body, UI controls and every figure (`font-variant-numeric: tabular-nums`). Chosen for readability, which matters when the subject is money.
- Both from Google Fonts with system fallbacks. Sentence case everywhere; no all-caps labels.

**Drawing rules.**
- Use Rough.js with a **fixed seed per element**, so lines look hand-drawn but do not wobble on every re-render.
- Projection chart: the P10–P90 range is drawn as **hatching** (diagonal pen strokes), denser in the P25–P75 band, so likelier outcomes literally have more ink. The median is a confident pen line; the target is a dashed line ending in a small cairn of stacked stones at the goal date.
- While a slider is being dragged, render the bands as smooth SVG paths for speed; re-sketch them with Rough.js when the slider is released (about 150 ms after the last change).
- Annotations are hand-drawn arrows and circled notes pointing at the relevant part of a chart ("this is the middle scenario").
- Jargon terms in text get a hand-drawn dotted underline (rough-notation). Tapping one makes Pebble explain it.

**Motion.**
- The signature moment: lines **draw themselves** (stroke-dashoffset), as if Pebble is sketching them with its pencil. Used for chart first-paint, arrows and the landing hero.
- On the landing page, one orchestrated sequence on load: Pebble walks in, sketches the projection, and points at it (about 2.5 s, skippable by scrolling or clicking).
- After that, motion responds to the user: bands reshape as sliders move, the time machine morphs the allocation, the stress test replays a drawdown in red pen.
- Lenis smooth scrolling on the landing page only.
- With `prefers-reduced-motion`: no Lenis, no draw-on animation (lines appear complete), Pebble holds still poses and changes pose without movement.

**Layout.** Left-aligned content on the notebook grid, generous margins, a 12-column grid on desktop collapsing to one column on mobile. Paper "cards" (slightly rotated by ±0.5°, with a taped corner) are used only for genuinely separate objects, such as goals.

**Quality floor.** Responsive down to 360 px, visible keyboard focus (drawn as a hand-drawn ring), AA contrast for text, every chart has a text summary for screen readers, hand-drawn elements never carry information that is not also in text.

**Copy.** Plain, specific, active voice. Buttons say what happens ("See my projection", "Create goal", "Replay 2008"). Errors say what happened and what to do. Every page footer: "Demo project. Simplified assumptions, not investment advice."

---

## Pebble, the guide robot

Pebble is a small, original robot drawn in the same pen style as the rest of the app. It is not modelled on any existing robot or character.

**Look.** A rounded, slightly uneven stone-shaped body (a nod to the cairn), a small screen face showing two dot eyes and a line mouth, short stubby arms, one antenna, and a pencil it holds in one hand. Drawn as layered SVG parts (body, face, eyes, mouth, arms, antenna, pencil) so each part can be animated separately.

**Poses and states.**

| State | When | Animation |
|---|---|---|
| `idle` | default | gentle bob, blinks every 3–6 s at random |
| `walk` | moving to a new spot | small hops along a curved path |
| `point` | guiding attention | turns and points the pencil at a target element |
| `sketch` | charts drawing | scribbles with the pencil, synced to the draw-on animation |
| `explain` | speech bubble open | mouth moves while text appears, antenna light on |
| `think` | waiting for an explanation | eyes look up, three dots above the antenna |
| `sleep` | API cold start | "zzz" drawn above, wakes with a stretch when the API answers |
| `cheer` | goal reached or onboarding done | small jump, arms up |
| `worried` | stress test running | eyes wide, holds the pencil close |

**Behaviour.**
- Pebble lives in a fixed layer above the page and moves between anchors registered by components (`usePebbleAnchor(id)`), so it can walk to and point at any element.
- Speech bubbles are hand-drawn, use Architects Daughter, and show text with a short handwriting reveal. Bubbles have "Got it" and, when relevant, "Tell me more" (a more detailed explanation).
- A guided tour on first visit of each main screen (three or four stops), stored as seen in `localStorage` and replayable from a "Show me around" button.
- Pebble never blocks content: on mobile it docks as a small avatar in the bottom corner and opens explanations as a bottom sheet.
- A visible "Quiet Pebble" toggle hides it and turns explanations into plain inline panels. The app must be fully usable with Pebble hidden.

---

## Slices

### Slice 0 — Repository scaffold

- Create the layout above with empty packages.
- `api/`: `uv init`, dependencies (fastapi, uvicorn[standard], pydantic-settings, sqlalchemy, alembic, psycopg[binary], numpy, structlog, sentry-sdk[fastapi], openai, httpx), dev dependencies (pytest, pytest-cov, hypothesis, mypy, ruff). Configure ruff (line length 100, rule set including `I`, `B`, `UP`, `SIM`) and mypy strict in `pyproject.toml`.
- `web/`: Vite React TS template, ESLint, Prettier, Vitest, `strict: true`.
- Root: `.gitignore`, `.editorconfig`, `.env.example` files in `api/` and `web/`, pre-commit config running ruff and prettier.
- Checks: `uv run ruff check .`, `npm run build`.

**Commit:** `chore: scaffold monorepo with api and web tooling`

### Slice 1 — API skeleton and local database

- App factory in `main.py`, settings in `config.py` (database URL, CORS origins, Sentry DSN, OpenAI key and model, environment name).
- `GET /health` returns status and checks the database connection.
- JSON logging with structlog, a request-ID middleware that sets and returns `X-Request-ID`.
- `infra/docker-compose.yml` with `postgres:16` and the API (multi-stage Dockerfile in `api/`, non-root user).
- SQLAlchemy engine and session dependency; Alembic initialised against the models' metadata.
- Tests: health endpoint (with a test database via a pytest fixture), request ID round-trip.

**Commit:** `feat(api): bootstrap FastAPI app with health check, logging and Postgres`

### Slice 2 — Risk profiles and model portfolios

- `domain/profiles.py`: five profiles (Prudent, Moderate, Balanced, Dynamic, Bold) mapped to target weights over four asset classes: global equity, emerging equity, euro government bonds, money market.
- Capital-market assumptions as one documented constant table: expected annual return, volatility, and a 4×4 correlation matrix. Comment that these are illustrative.
- `score_questionnaire(answers) -> RiskProfile`: six questions (horizon, income stability, reaction to a 20% drop, experience, share of savings, goal flexibility), each answer scored, total mapped to a profile.
- Endpoints: `GET /profiles`, `GET /questionnaire`, `POST /questionnaire/score`.
- Tests: weights sum to 1 for every profile; scoring is monotonic (more risk-tolerant answers never yield a more prudent profile), property-tested with Hypothesis.

**Commit:** `feat(domain): add risk questionnaire, profiles and model allocations`

### Slice 3 — Monte Carlo simulation engine

- `domain/simulation.py`: vectorised NumPy simulation with monthly steps. Inputs: initial amount, monthly contribution, horizon in months, allocation weights (or a glide-path function, added in slice 4), number of paths (default 5,000), seed.
- Portfolio return per month drawn from a multivariate normal on log returns built from the assumptions and correlations.
- Output: P10, P25, P50, P75, P90 per month, total contributed per month, probability of ending at or above a target.
- `POST /simulations` with Pydantic validation (horizon 1–40 years, amounts ≥ 0, sane caps).
- Same seed returns identical results; response includes the seed.
- Performance budget: 5,000 paths × 40 years under 150 ms on a laptop; add a test that asserts it under a generous bound.
- Tests: zero volatility reproduces the deterministic compound-interest result; percentiles are ordered; a higher contribution never lowers the success probability.

**Commit:** `feat(simulation): add vectorised Monte Carlo goal projection`

### Slice 4 — Glide path

- `domain/glide_path.py`: `allocation_at(profile, months_remaining)`. Full profile risk when 10+ years remain, then a linear shift from equity toward bonds and money market, reaching a capital-preservation mix at the goal date.
- The simulation accepts the glide path so the allocation changes month by month.
- `GET /glide-path?profile=…&horizon_months=…` returns the allocation for each year, for the time-machine view.
- Tests: equity share never increases as months remaining decrease; weights always sum to 1; at zero months the allocation equals the preservation mix.

**Commit:** `feat(investment): add horizon-based glide path`

### Slice 5 — Goals and persistence

- Models: `User` (a single seeded demo user; the API is demo-scoped with no authentication, documented in an ADR), `Goal` (name, type, target cents, target date, monthly contribution cents, profile, created_at).
- Alembic migration.
- Services and endpoints: create, list, get, update, delete goals; `GET /goals/{id}/projection` runs the glide-path simulation for the goal.
- Tests: CRUD happy paths, validation errors return 422 with clear messages, unknown goal returns 404.

**Commit:** `feat(goals): persist goals with Alembic migrations and projection endpoint`

### Slice 6 — Double-entry ledger

- Models: `Account` (owner, kind: `external_bank`, `cash`, `holding:<asset_class>`, `fees`), `JournalEntry` (id, goal_id, kind, idempotency_key unique, created_at, description), `JournalLine` (entry_id, account_id, amount_cents signed).
- Invariant: the lines of every entry sum to zero, enforced in the service before insert and verified by reconciliation.
- `services/ledger.py`: `post_entry(...)` inside one transaction; a repeated `idempotency_key` returns the original entry instead of creating a new one.
- Endpoints: `POST /goals/{id}/deposits` (requires an `Idempotency-Key` header; invests the deposit into holdings according to the current allocation), `GET /goals/{id}/balance`, `GET /goals/{id}/entries`, `GET /ledger/reconciliation` (verifies every entry balances and per-account balances equal the sum of their lines).
- Tests: Hypothesis generates random sequences of deposits and fees and asserts the global balance is always zero and reconciliation always passes; sending the same deposit twice creates one entry.

**Commit:** `feat(ledger): add double-entry ledger with idempotent deposits and reconciliation`

### Slice 7 — Drift-based rebalancing

- `domain/rebalancing.py`: pure function that takes current holdings and target weights and returns transfers between holding accounts when any asset class drifts more than 5 percentage points from target. Transfers in whole cents, summing to zero.
- Price movements: a small deterministic `mark_to_market(goal, month)` that applies seeded monthly returns to holdings, so drift actually happens in the demo.
- `POST /goals/{id}/rebalance` (idempotent per goal and date) posts one journal entry of kind `rebalance`; `GET /goals/{id}/rebalances` lists them.
- Tests: no transfers when within threshold; after rebalancing, weights are within one cent rounding of target; transfers always balance.

**Commit:** `feat(investment): add drift-based rebalancing posted to the ledger`

### Slice 8 — Historical stress tests

- `domain/stress.py`: three stylised scenarios as monthly return paths per asset class, clearly commented as approximations: global financial crisis 2008 (deep equity drawdown over about 17 months, government bonds positive), Covid shock 2020 (sharp one-month equity fall and fast recovery), rate shock 2022 (equities and bonds falling together).
- `POST /goals/{id}/stress-tests/{scenario}` replays the scenario on the goal's current allocation, with and without rebalancing, and returns both value paths plus maximum drawdown and months to recover.
- Tests: scenario paths have the documented length; the replay with zero equity exposure has a smaller drawdown than with full equity in the 2008 scenario.

**Commit:** `feat(simulation): add historical stress-test replays`

### Slice 9 — Explainability layer (GenAI)

The goal of this layer is to translate finance into everyday language. It is what Pebble says.

- `explain/facts.py`: builders that turn engine outputs into a small, typed **facts** object per topic. Topics: `projection`, `allocation`, `glide_path`, `rebalance`, `stress_test`, `ledger_entry`, `term`. Example for `projection`: target, horizon, monthly contribution, P10/P50/P90 at the goal date, success probability, profile name.
- `explain/glossary.py`: a curated glossary of about 25 terms with a short, human-written plain-language definition and an everyday analogy for each (for example volatility, diversification, ETF, bond, money market, percentile, drawdown, rebalancing, glide path, compound growth, risk profile, inflation). French and English. This is both the grounding for the model and the fallback.
- `POST /explain`: request contains `topic`, `facts` (or a `term`), `level` (`simple` or `more_detail`) and `language` (`fr` or `en`). Response: `title`, `body` (at most 60 words for `simple`, 140 for `more_detail`), optional `analogy`, `terms_used` (glossary keys the UI can underline), and `source` (`ai` or `fallback`).
- `explain/client.py`: one thin wrapper around the official `openai` SDK using structured outputs into the response model. Model name from `OPENAI_MODEL`. Timeout 10 s, one retry, token cap. The system prompt sets the voice: friendly, concrete, no jargon without explaining it, no advice, no promises about returns, uses only the numbers in the facts.
- **Number guard:** every number in the generated text must appear in the facts (allowing formatting differences such as "12 000 €" for 1200000 cents, and rounded percentages). If not, the response is replaced by the template fallback and the event is logged.
- **Fallbacks:** without an API key, or on timeout, error or a failed guard, use deterministic templates per topic filled with the facts, plus the glossary entry for terms. The UI behaves identically.
- **Cache:** responses cached in memory keyed by a hash of topic, facts, level and language, so the same explanation is never paid for twice.
- Simple in-memory rate limit per client IP on `/explain`.
- Tests: the OpenAI client is mocked; every topic has a working fallback; the guard rejects text containing an unknown figure; the cache returns the stored response on a second identical call.
- Add `docs/adr/0003-llm-boundaries.md` explaining why the model only explains and never computes.

**Commit:** `feat(explain): add plain-language explainability layer with guarded GenAI and fallbacks`

### Slice 10 — Monitoring and CI

- Sentry in the API (FastAPI integration, environment tag, release from git SHA, request ID attached as a tag); no-op without a DSN.
- `.github/workflows/ci.yml`: an `api` job (Postgres service container, uv, ruff, mypy, pytest with coverage, fail under 85% on `domain/`, `services/` and `explain/`) and a `web` job (npm ci, lint, typecheck, test, build). Cache dependencies.
- PR and issue templates in `.github/`. Document in the README how Sentry issues are linked to GitHub Issues.
- `GET /debug/sentry` only when `ENVIRONMENT=local`, to verify error reporting.

**Commit:** `ci: add GitHub Actions pipeline, Sentry monitoring and repo templates`

### Slice 11 — Web foundation and notebook design system

- Tailwind configured with the palette tokens as CSS variables for notebook (light) and blueprint (dark) themes, with a theme toggle drawn as a pencil-and-chalk switch.
- Notebook grid background as a lightweight CSS background (no images).
- Fonts loaded, type scale defined (Architects Daughter for headings and annotations, Atkinson Hyperlegible for body, UI and figures at 16–18 px).
- Hand-drawn primitives built on Rough.js with fixed seeds: `SketchBox`, `SketchButton`, `SketchArrow`, `SketchCircle`, `SketchUnderline`, `SketchRing` (focus ring), and a `useDrawOn` hook for the self-drawing stroke animation.
- Form controls: `Slider` (hand-drawn track, pencil-tip thumb, keyboard accessible), `Field`, `Sheet`, `Toast`, `Skeleton` (drawn as scribbled placeholder lines).
- `Figure` component for money and percentages (tabular numbers, `Intl.NumberFormat('fr-FR')` or `en-GB` by language).
- Router with routes: `/`, `/start`, `/simulate`, `/goals`, `/goals/:id`. Language toggle (FR / EN) stored in `localStorage` and sent to `/explain`.
- API client: types generated from the OpenAPI schema with `openapi-typescript` (`npm run gen:api`), TanStack Query hooks per resource, base URL from `VITE_API_URL`.
- Sentry for React, no-op without a DSN.
- Tests: `Figure` formatting; `useDrawOn` returns finished state immediately under reduced motion.

**Commit:** `feat(web): add notebook design system, hand-drawn primitives and typed API client`

### Slice 12 — Pebble, the guide robot

- `web/src/pebble/`: the layered SVG robot as described in the Pebble section, with each state from the table implemented as Framer Motion variants.
- `PebbleProvider` with an API: `pebble.say({ topic, facts | term })`, `pebble.pointAt(anchorId)`, `pebble.setState(state)`, `pebble.tour(steps)`. `usePebbleAnchor(id)` registers elements Pebble can walk to.
- Speech bubble component: hand-drawn outline, handwriting reveal of the text, "Got it" and "Tell me more" (requests `level: more_detail`), and tappable underlined terms that chain to a `term` explanation.
- Calls `/explain` through TanStack Query; shows the `think` state while loading.
- Cold-start handling: if the first API call takes over two seconds, Pebble shows `sleep` with the line "The demo server is waking up. This takes a few seconds." and switches to `idle` with a stretch when the API answers. Render free instances sleep when idle.
- "Quiet Pebble" toggle; on mobile Pebble docks as a small avatar and explanations open as a bottom sheet.
- Reduced motion: static poses only.
- Tests: provider queues messages in order; quiet mode renders explanations inline; anchors unregister on unmount.

**Commit:** `feat(web): add Pebble guide robot with explanations, tours and states`

### Slice 13 — Landing page

- Hero: the signature sequence. Pebble walks onto the notebook page and sketches a projection for an example goal, the hatched bands drawing in, then points at the median line with a handwritten note. A single slider beside it ("Monthly savings") reshapes the drawing live. Headline: "See where your savings could take you."
- Three short scroll sections in plain language, each built from a real fragment of the product sketched on the page: "You set a goal" (a goal card taped to the page), "Your portfolio gets safer as the date gets closer" (a small glide-path strip), "Every euro is accounted for" (a ledger line with a hand-drawn tick).
- Call to action: "Plan my first goal" leading to `/start`.
- Lenis smooth scroll on this page only, disabled with reduced motion.
- Lighthouse performance and accessibility both 90+ on mobile; lazy-load below-the-fold drawings.

**Commit:** `feat(web): add landing page with self-sketching hero and Pebble intro`

### Slice 14 — Onboarding

- Step 1: choose a goal type from hand-drawn icon cards (retirement, home, safety net, studies, other), then name, target amount and date as simple fields. Pebble explains why the date matters.
- Step 2: the six-question risk questionnaire, one question per screen on mobile, with a hand-drawn progress line (a real sequence, so step numbering is fine). Pebble reacts briefly to each answer.
- Step 3: profile reveal. The allocation is sketched as a stacked bar that draws itself, Pebble does `cheer`, then explains the profile in plain language (`/explain` topic `allocation`). Button: "See my projection".
- Creates the goal on confirmation and routes to `/goals/:id`.

**Commit:** `feat(web): add onboarding flow with sketched profile reveal`

### Slice 15 — Live simulator

- `/simulate`: sliders for initial amount, monthly contribution, horizon, and a profile switcher. Debounced requests (150 ms), keeping the previous drawing on screen while loading so it never flashes.
- The hatched projection chart: P10–P90 and P25–P75 hatching, median pen line, dashed target with the cairn glyph, contributions line in graphite for comparison, hand-written axis labels.
- Headline figure: chance of reaching the goal, highlighted with rough-notation in `--highlighter`.
- "What does this mean?" makes Pebble walk to the chart, point at the median, and explain the projection (`/explain` topic `projection`). Hand-drawn arrows annotate P10 ("a tough market") and P90 ("a great market").
- Text summary of the chart for screen readers.

**Commit:** `feat(web): add live simulator with hatched projection chart and explanations`

### Slice 16 — Goal dashboard, time machine and stress test

- `/goals`: goals as taped paper cards with a hand-drawn progress ring, current value against median projection, and the next milestone.
- `/goals/:id`: balance, allocation, deposit form (sends an idempotency key generated per submission), ledger history as a handwritten-style table with crisp figures, rebalance history. Tapping a ledger line or a rebalance makes Pebble explain it (`ledger_entry`, `rebalance`).
- Time machine: a horizontal scrubber over the years to the goal; dragging morphs the sketched allocation bar and shows the projection at that year. Pebble explains the glide path the first time it is used.
- Stress test panel: "Replay 2008", "Replay 2020", "Replay 2022". The replay draws the value path in `--red-pen`, compares with and without rebalancing, and states the maximum drawdown and months to recover in a sentence. Pebble goes `worried` during the drop and explains the result afterwards (`stress_test`).
- Empty states that invite action ("No deposits yet. Add your first deposit to start the ledger.").

**Commit:** `feat(web): add goal dashboard, time-machine scrubber and stress-test replays`

### Slice 17 — Demo data, Metabase and Kubernetes

- `api/scripts/seed.py`: creates the demo user, three goals with different profiles and horizons, 24 months of deposits, mark-to-market and rebalances, all through the services so the ledger stays consistent. Safe to run twice.
- Metabase service in `docker-compose.yml`; `docs/metabase.md` describing three questions: assets per goal type, rebalancing events per month, reconciliation status.
- `infra/k8s/`: Deployment, Service, ConfigMap, and a Secret template for the API, with readiness and liveness probes on `/health` and resource requests. Validated with `kubectl apply --dry-run=client` in CI if `kubectl` is available, otherwise skipped.

**Commit:** `chore: add demo seed data, Metabase setup and Kubernetes manifests`

### Slice 18 — Deployment

- `render.yaml` blueprint: a web service built from `api/Dockerfile` with `alembic upgrade head` before start, the seed script run once, and a managed PostgreSQL database. Environment variables listed with `sync: false` for secrets.
- `web/vercel.json` with SPA rewrites; document `VITE_API_URL`.
- CORS restricted to the Vercel domain plus localhost.
- `docs/deploy.md` with the exact steps and a note to check Render's current free-tier limits for web services and databases.

**Commit:** `chore(deploy): add Render blueprint and Vercel configuration`

### Slice 19 — Documentation polish

- Finish `README.md`: live demo link, demo GIF placeholder, features, architecture diagram (Mermaid), "How this maps to the role" table, run locally, tests, decision records index, AI usage notes.
- ADRs in `docs/adr/`: `0001-integer-cents-and-double-entry.md`, `0002-drift-based-rebalancing.md`, `0003-llm-boundaries.md` (from slice 9), `0004-demo-scope-without-auth.md`, `0005-hand-drawn-ui-with-exact-figures.md`.
- `docs/ai-usage.md`: how Claude Code was used to build the project, where its output was rejected or rewritten, and how correctness was verified (tests, property tests, manual review).

**Commit:** `docs: add architecture, decision records and AI usage notes`

### Slice 21 — Support view

Purpose: an internal page for a customer-support agent to understand a client's account quickly and answer "what happened to my money?" questions in plain language.

**Backend**
- Seed: extend `api/scripts/seed.py` with 5 more demo clients (varied profiles, goals, deposits, rebalances, one client with a large market drop in a given month). Keep it idempotent.
- Endpoints (prefix `/support`, demo-scoped, no auth, documented in ADR 0004):
  - `GET /support/clients?query=`: search by name or email, paginated.
  - `GET /support/clients/{id}`: summary (goals, profile, total balance, total contributed, last activity).
  - `GET /support/clients/{id}/timeline?from=&to=`: a single chronological list merging ledger entries (deposits, fees, rebalances) and monthly market moves (value change per goal from `mark_to_market`). Each event has type, date, amount_cents, goal, and a short machine-readable payload.
  - `POST /support/clients/{id}/ask`: body `{ question, month? }`. Builds facts **only** from the timeline (e.g. balance at start and end of month, deposits, fees, rebalances, market effect per asset class), then calls the explainability layer with a new topic `support_answer`. The answer must break the balance change into its parts (market effect, deposits, fees) and the parts must sum to the total change, computed in code before calling the model. Number guard and template fallback apply as for every topic.
- Tests: timeline is ordered and complete versus the ledger; the decomposition sums exactly to the balance change in cents; fallback answer works without an OpenAI key; unknown client returns 404.

**Frontend**
- Route `/support`, linked discreetly in the footer as "Support view (internal demo)".
- Layout: search on the left, client summary and timeline in the centre (hand-drawn timeline line, events as small sketched markers, figures in Atkinson Hyperlegible), a question panel on the right.
- The question panel offers suggested questions ("Why did the balance go down in March?", "When was the last rebalance?") and a free-text box. Pebble answers in a speech bubble and the matching timeline events get highlighted with rough-notation.
- Clicking a timeline event makes Pebble explain that single event.
- Empty state: "Search for a client to see their account history."
- Tests: search renders results; asking a question highlights the events referenced in the answer.

**Commit:** `feat(support): add support view with client timeline and plain-language answers`

---

## Definition of done

- All slices committed in order with the exact messages.
- CI green on `main`.
- `docker compose up` gives a working API, database and Metabase; `npm run dev` gives the web app against it.
- The deployed web app loads on a phone, survives a cold API start with Pebble asleep, and works fully with the OpenAI key removed and with Pebble set to quiet.
