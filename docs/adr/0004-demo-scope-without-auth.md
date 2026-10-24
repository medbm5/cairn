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
- Abuse is limited by validation caps on every amount and horizon, by a rate limit on the only
  endpoint that costs money (`/explain`), and by the fact that nothing stored is sensitive.

## Consequences

- Anyone with the URL can create, change or delete demo goals. The seed script can be rerun to
  restore the demo data.
- The deployed demo must never be used with real personal or financial data. The footer of every
  page says it is a demo with simplified assumptions.
- Moving to multiple users would require: an identity provider, a `current_user` dependency,
  filtering every query by owner, and tests for cross-user access.
