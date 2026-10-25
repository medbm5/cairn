# 0004 Demo scope without authentication

- Status: accepted
- Date: 2026-10-24

## Context

Cairn is a public demo. Visitors should be able to open the link and try every feature in
seconds, without creating an account. The data it holds is invented: one demo person, a few
goals and their ledger.

Real authentication (sign-up, password reset, sessions, per-user authorisation on every query)
would add a large surface that the demo does not need, and would make the core ideas (the
simulation, the glide path, the ledger) harder to review.

## Decision

- The database has a `users` table with a single seeded **demo user**. Every goal belongs to it.
- The API has **no authentication**. All endpoints act on the demo user's data.
- The service layer still goes through `demo_user(session)` when creating goals, so ownership is
  modelled and adding real users later means replacing that one function with "the current user".
- The **support view** (`/support/...` endpoints and the `/support` page) is also demo-scoped
  and unauthenticated. It reads invented clients, seeded with `example.com` addresses next to the
  demo user, who stays the first user and the only one the rest of the app acts for (the goals
  list only shows the demo user's goals). The endpoints are: `GET /support/clients?query=`
  (search by name or email, paginated), `GET /support/clients/{id}` (summary),
  `GET /support/clients/{id}/timeline?from=&to=` (ledger entries and monthly market moves in one
  chronological list) and `POST /support/clients/{id}/ask` (a plain-language answer built only
  from that timeline). The page is linked discreetly from the footer as an internal demo.
- The **observability page** (`GET /observability/stats` and `/observability`) is open in the
  same way. It shows request paths, status codes, timings, token counts and log events, never
  request bodies, support questions or keys.
- Abuse is limited by validation caps on every amount and horizon, by one shared rate limit on
  the endpoints that can call the model (`/explain` and `/support/clients/{id}/ask`), and by the
  fact that nothing stored is sensitive.

## Consequences

- Anyone with the URL can create, change or delete demo goals. The seed script can be rerun to
  restore the demo data.
- The deployed demo must never be used with real personal or financial data. The footer of every
  page says it is a demo with simplified assumptions.
- Moving to multiple users would require: an identity provider, a `current_user` dependency,
  filtering every query by owner, and tests for cross-user access.
- A real support tool would sit behind staff authentication with role-based access and an audit
  log of every client record viewed. Here anyone with the URL can read the invented clients' data,
  which is acceptable only because none of it is real.
