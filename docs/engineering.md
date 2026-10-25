# Engineering notes

The details behind Cairn, for developers and reviewers. The [README](../README.md) is the short
version.

## Code map

```mermaid
flowchart LR
  subgraph Web["Web app (React + TypeScript, Vercel)"]
    UI[Screens and hand-drawn charts] --- P[Pebble]
  end
  subgraph API["API (FastAPI, Render)"]
    R[Routers] --> SV[Services<br/>goals, ledger, support]
    R --> E[Explainability layer<br/>facts, number guard, templates]
    SV --> DM[Domain, pure functions<br/>profiles, simulation, glide path,<br/>rebalancing, stress tests]
    E -. facts from .-> DM
    R --> OB[Observability<br/>requests, AI calls, log trail]
  end
  UI -->|REST, typed client| R
  P -->|POST /explain| E
  E -->|optional| O[OpenAI API]
  SV --> D[(PostgreSQL)]
  API --> S[Sentry]
  Web --> S
  D --> M[Metabase]
```

- **Domain** (`api/src/cairn/domain`): pure, typed functions with no I/O, covered by unit and
  property-based tests.
- **Services** (`api/src/cairn/services`): use cases that combine the domain with the database.
  All money moves through `post_entry`, which only accepts balanced entries.
- **Explainability** (`api/src/cairn/explain`): facts in, plain words out. A guard checks that
  every number in a generated text comes from the facts; otherwise a written template is used.
- **Routers** (`api/src/cairn/routers`): a thin HTTP layer with Pydantic validation.
- **Web** (`web/src`): screens in `routes/`, features in `features/`, Pebble in `pebble/`,
  charts in `charts/`, hand-drawn primitives in `components/sketch/`. API types are generated
  from the OpenAPI schema.

## The language model

- Default model: `gpt-5-nano` with minimal reasoning effort, the cheapest current option; set
  `OPENAI_MODEL` to change it. Without `OPENAI_API_KEY` everything uses written templates.
- Token budget: a short system prompt, facts sent as compact JSON with amounts already in euros
  (only the facts a question needs), a 400-token output cap, an in-memory cache, and no model call
  at all for glossary terms, whose definitions are written by hand.
- Every call is recorded with its tokens, latency and estimated cost, visible on `/observability`.
  Prices live in `api/src/cairn/observability.py`; check OpenAI's pricing page when they change.
- See [ADR 0003](adr/0003-llm-boundaries.md) for why the model only explains and never computes.

## Observability

- **The `/observability` page** shows the last 24 hours: request counts, server error rate and
  latency per route; where each explanation came from (AI, cache or template, and why); tokens
  and estimated cost per topic; and a trail of recent requests and log lines that can be filtered
  to a single request ID. It reads `GET /observability/stats`.
- **Storage:** events are buffered in memory (so recording never slows a request) and written to
  the `observability_events` table by a background thread every
  `OBSERVABILITY_FLUSH_SECONDS` (5 s); the stats endpoint also writes what is pending before it
  reads. A restart loses at most those few seconds. Events older than
  `OBSERVABILITY_RETENTION_DAYS` (7) are pruned hourly. If the database is down, events are
  dropped and a warning is logged: observability never takes the API down.
- **Logs** are JSON lines (structlog). Every request gets an `X-Request-ID` (reused if the client
  sends one), returned in the response and attached to every log line.
- **Sentry** captures errors from the API and the web app when `SENTRY_DSN` / `VITE_SENTRY_DSN`
  are set; without them it is a no-op. Events carry the environment, the release (the git SHA,
  from `RENDER_GIT_COMMIT` on Render) and the request ID as a tag.
- **Checking the setup:** with `ENVIRONMENT=local`, `GET /debug/sentry` raises a test error.

### From a Sentry issue to a GitHub issue

1. In Sentry, install the GitHub integration (Settings → Integrations → GitHub) and give it
   access to this repository.
2. In the project's settings, add the repository under *Code Mappings* (`api/src/` → `src/`,
   `web/src/` → `src/`) so stack traces link to the right lines.
3. On any Sentry issue, use **Link GitHub Issue** (or *Create GitHub Issue*). The GitHub issue
   gets the Sentry link, and the bug template asks for the request ID.
4. Mention `Fixes SENTRY-ID` in the pull request or commit that fixes it; Sentry resolves the
   issue when that release is deployed.

## Running without Docker, and other chores

- API with uv: `cd api && uv sync && uv run alembic upgrade head && uv run uvicorn
  cairn.main:app --reload` (it needs a PostgreSQL `DATABASE_URL`).
- Demo data: `uv run python scripts/seed.py` (safe to run twice).
- After changing the API, regenerate the web app's types:
  `cd api && uv run python scripts/export_openapi.py && cd ../web && npm run gen:api`.
- [Deploying to Render and Vercel](deploy.md) · [Metabase questions](metabase.md).

## Tests

```bash
# API: lint, format, strict typing, unit and property-based tests
cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest
uv run pytest --cov=cairn.domain --cov=cairn.services --cov=cairn.explain   # CI requires 85%
TEST_DATABASE_URL=postgresql+psycopg://cairn:cairn@localhost:5432/cairn_test uv run pytest
# (tests use in-memory SQLite unless TEST_DATABASE_URL points at Postgres, as in CI)

# Web: lint, types, component and utility tests, production build
cd web && npm run lint && npm run typecheck && npm run test && npm run build
```

## How this maps to the role

| Requirement | Where it lives |
|---|---|
| Python backend, FastAPI | `api/src/cairn` |
| PostgreSQL | SQLAlchemy 2.0 models, Alembic migrations |
| Robo-advisor algorithms | Monte Carlo engine, glide path, drift rebalancing in `api/src/cairn/domain` |
| Accounting reliability | Double-entry ledger, idempotent deposits, reconciliation endpoint |
| Quality and code review | ruff, mypy strict, pytest + Hypothesis, PR templates |
| CI/CD | GitHub Actions, Vercel and Render deployments |
| Monitoring and bug tracking | Sentry linked to GitHub Issues, JSON logs, request IDs, `/observability` |
| Kubernetes, Metabase | `infra/k8s`, Metabase in Docker Compose |
| AI with discernment | Guarded explainability layer with fallbacks, caching and cost tracking |
| Working with support and product | The support view: a client's timeline and plain-language answers |

## Decision records

- [0001 Integer cents and double-entry ledger](adr/0001-integer-cents-and-double-entry.md)
- [0002 Drift-based rebalancing](adr/0002-drift-based-rebalancing.md)
- [0003 Boundaries for the language model](adr/0003-llm-boundaries.md)
- [0004 Demo scope without authentication](adr/0004-demo-scope-without-auth.md)
- [0005 Hand-drawn interface with exact figures](adr/0005-hand-drawn-ui-with-exact-figures.md)

## Build roadmap

The project was built in small, reviewable slices, one commit each. Full specifications are in
[BUILD_PLAN.md](../BUILD_PLAN.md).

| # | Slice | Commit message |
|---|---|---|
| 0 | Repository scaffold | `chore: scaffold monorepo with api and web tooling` |
| 1 | API skeleton and database | `feat(api): bootstrap FastAPI app with health check, logging and Postgres` |
| 2 | Risk profiles | `feat(domain): add risk questionnaire, profiles and model allocations` |
| 3 | Monte Carlo engine | `feat(simulation): add vectorised Monte Carlo goal projection` |
| 4 | Glide path | `feat(investment): add horizon-based glide path` |
| 5 | Goals and persistence | `feat(goals): persist goals with Alembic migrations and projection endpoint` |
| 6 | Double-entry ledger | `feat(ledger): add double-entry ledger with idempotent deposits and reconciliation` |
| 7 | Rebalancing | `feat(investment): add drift-based rebalancing posted to the ledger` |
| 8 | Stress tests | `feat(simulation): add historical stress-test replays` |
| 9 | Explainability layer | `feat(explain): add plain-language explainability layer with guarded GenAI and fallbacks` |
| 10 | Monitoring and CI | `ci: add GitHub Actions pipeline, Sentry monitoring and repo templates` |
| 11 | Notebook design system | `feat(web): add notebook design system, hand-drawn primitives and typed API client` |
| 12 | Pebble, the guide robot | `feat(web): add Pebble guide robot with explanations, tours and states` |
| 13 | Landing page | `feat(web): add landing page with self-sketching hero and Pebble intro` |
| 14 | Onboarding | `feat(web): add onboarding flow with sketched profile reveal` |
| 15 | Live simulator | `feat(web): add live simulator with hatched projection chart and explanations` |
| 16 | Dashboard, time machine, stress test | `feat(web): add goal dashboard, time-machine scrubber and stress-test replays` |
| 17 | Demo data, Metabase, Kubernetes | `chore: add demo seed data, Metabase setup and Kubernetes manifests` |
| 18 | Deployment | `chore(deploy): add Render blueprint and Vercel configuration` |
| 19 | Documentation | `docs: add architecture, decision records and AI usage notes` |
| 21 | Support view | `feat(support): add support view with client timeline and plain-language answers` |

## Built with AI

Claude Code built this project slice by slice from [BUILD_PLAN.md](../BUILD_PLAN.md). Every slice
had to pass linting, strict typing and tests before it was committed, and the invariants that
protect money (balanced entries, exact cent splits, reconciliation, idempotent deposits) are
property-tested. See [ai-usage.md](ai-usage.md) for what was caught and rewritten along the way.
