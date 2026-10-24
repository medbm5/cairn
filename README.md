# Cairn

**Plan a life goal on paper with Pebble, a little robot that explains investing in everyday words.**

[Live demo](https://your-app.vercel.app) · [API docs](https://your-api.onrender.com/docs)
<!-- Replace both links once deployed (see docs/deploy.md). -->

<!-- Demo GIF placeholder: record the landing sketch, onboarding and a 2008 replay, save it as
     docs/demo.gif, then replace this comment with: ![Cairn demo](docs/demo.gif) -->
_Demo GIF coming soon._

> Demo project built to explore goal-based investing. Simplified assumptions, not investment advice. Not affiliated with any company.

---

## What you can do

- **Set a goal** (retirement, a home, a safety net) and find your risk profile with six quick questions.
- **Watch your plan being sketched.** Pebble draws your projection on a notebook page. Drag the sliders and the range of possible outcomes reshapes instantly, with your chance of reaching the goal.
- **Understand every word.** Tap any finance term, or ask "What does this mean?", and Pebble explains it in plain French or English, with an everyday analogy.
- **Travel through time.** Scrub through the years and see your allocation shift from growth to safety as the goal approaches.
- **Replay a crisis.** See how your portfolio would have behaved in 2008, 2020 and 2022, with and without rebalancing.
- **Follow every euro.** Each deposit and rebalance is recorded in a double-entry ledger that always balances.
- **Answer support questions.** An internal support view shows a client's account as one timeline; ask "Why did the balance go down in March?" and Pebble splits the change into market effect, deposits and fees, to the cent.

## How it works

```mermaid
flowchart LR
  subgraph Web["Web app (React + TypeScript, Vercel)"]
    UI[Screens and hand-drawn charts] --- P[Pebble]
  end
  subgraph API["API (FastAPI, Render)"]
    R[Routers] --> SV[Services<br/>goals, ledger]
    R --> E[Explainability layer<br/>facts, number guard, templates]
    SV --> DM[Domain, pure functions<br/>profiles, simulation, glide path,<br/>rebalancing, stress tests]
    E -. facts from .-> DM
  end
  UI -->|REST, typed client| R
  P -->|POST /explain| E
  E -->|optional| O[OpenAI API]
  SV --> D[(PostgreSQL)]
  API --> S[Sentry]
  Web --> S
  D --> M[Metabase]
```

- **Domain** (`api/src/cairn/domain`): pure, typed functions with no I/O. Easy to test, including
  with property-based tests.
- **Services** (`api/src/cairn/services`): use cases that combine the domain with the database.
  All money moves through `post_entry`, which only accepts balanced entries.
- **Routers** (`api/src/cairn/routers`): a thin HTTP layer with Pydantic validation.
- **Web** (`web/src`): screens in `routes/`, features in `features/`, Pebble in `pebble/`,
  charts in `charts/`, hand-drawn primitives in `components/sketch/`. API types are generated
  from the OpenAPI schema.

The simulation, glide path, rebalancing and ledger are deterministic Python code covered by unit and property-based tests. The explainability layer receives the facts the engine already computed and rewrites them in everyday language. A guard checks that every number in an explanation comes from those facts; otherwise a written template is used. The app works fully without an OpenAI key.

The interface is drawn by hand, like a plan sketched on a notebook (or a blueprint, in dark mode), but every figure is rendered in a crisp, highly legible typeface.

## How this maps to the role

| Requirement | Where it lives |
|---|---|
| Python backend, FastAPI | `api/src/cairn` |
| PostgreSQL | SQLAlchemy 2.0 models, Alembic migrations |
| Robo-advisor algorithms | Monte Carlo engine, glide path, drift rebalancing in `api/src/cairn/domain` |
| Accounting reliability | Double-entry ledger, idempotent deposits, reconciliation endpoint |
| Quality and code review | ruff, mypy strict, pytest + Hypothesis, PR templates |
| CI/CD | GitHub Actions, Vercel and Render deployments |
| Monitoring and bug tracking | Sentry (API and web) linked to GitHub Issues, JSON logs, request IDs |
| Kubernetes, Metabase | `infra/k8s`, Metabase in Docker Compose |
| AI with discernment | Guarded explainability layer with fallbacks and caching, `docs/ai-usage.md` |
| Working with support and product | Plain-language explanations of every screen, ledger line and rebalance |

## Run locally

```bash
# API (http://localhost:8000), database and Metabase (http://localhost:3000)
cp api/.env.example api/.env
docker compose -f infra/docker-compose.yml up --build
# Ports busy? API_PORT=8010 DB_PORT=5433 METABASE_PORT=3001 docker compose ... up

# Demo data: three goals with 24 months of history (safe to run twice)
docker compose -f infra/docker-compose.yml exec api python scripts/seed.py

# Web app (http://localhost:5173)
cd web
cp .env.example .env        # VITE_API_URL points at the API
npm install
npm run dev
```

The app runs without an OpenAI key or Sentry DSN; those features fall back gracefully.

Without Docker, run the API with uv: `cd api && uv sync && uv run alembic upgrade head &&
uv run uvicorn cairn.main:app --reload` (it needs a PostgreSQL `DATABASE_URL`).

After changing the API, regenerate the web app's types:
`cd api && uv run python scripts/export_openapi.py && cd ../web && npm run gen:api`.

More: [deploying to Render and Vercel](docs/deploy.md) · [Metabase questions](docs/metabase.md).

## Monitoring

- **Logs** are JSON lines (structlog). Every request gets an `X-Request-ID` (reused if the client
  sends one), which is returned in the response and attached to every log line.
- **Sentry** captures errors from the API and the web app when `SENTRY_DSN` / `VITE_SENTRY_DSN`
  are set; without them it is a no-op. Events carry the environment, the release (the git SHA,
  from `RENDER_GIT_COMMIT` on Render) and the request ID as a tag, so a Sentry event leads
  straight to the matching log lines.
- **Checking the setup:** with `ENVIRONMENT=local`, `GET /debug/sentry` raises a test error. The
  route does not exist in any other environment.

### From a Sentry issue to a GitHub issue

1. In Sentry, install the GitHub integration (Settings → Integrations → GitHub) and give it
   access to this repository.
2. In the project's settings, add the repository under *Code Mappings* (`api/src/` → `src/`,
   `web/src/` → `src/`) so stack traces link to the right lines.
3. On any Sentry issue, use **Link GitHub Issue** (or *Create GitHub Issue*). The GitHub issue
   gets the Sentry link, and the bug template asks for the request ID.
4. Mention `Fixes SENTRY-ID` (Sentry's short ID) in the pull request or commit that fixes it;
   Sentry resolves the issue when that release is deployed.

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

## Decision records

- [0001 Integer cents and double-entry ledger](docs/adr/0001-integer-cents-and-double-entry.md)
- [0002 Drift-based rebalancing](docs/adr/0002-drift-based-rebalancing.md)
- [0003 Boundaries for the language model](docs/adr/0003-llm-boundaries.md)
- [0004 Demo scope without authentication](docs/adr/0004-demo-scope-without-auth.md)
- [0005 Hand-drawn interface with exact figures](docs/adr/0005-hand-drawn-ui-with-exact-figures.md)

## Build roadmap

The project was built in small, reviewable slices, one commit each. Full specifications are in [BUILD_PLAN.md](BUILD_PLAN.md).

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

Claude Code built this project slice by slice from [BUILD_PLAN.md](BUILD_PLAN.md). Every slice had to pass linting, strict typing and tests before it was committed, and the invariants that protect money (balanced entries, exact cent splits, reconciliation, idempotent deposits) are property-tested. At runtime the language model only rephrases figures the engine computed, behind a number guard. See [docs/ai-usage.md](docs/ai-usage.md) for what was caught and rewritten along the way, and for the human review still to record.
