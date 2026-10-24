# 0002 Drift-based rebalancing

- Status: accepted
- Date: 2026-10-24

## Context

Markets move asset classes at different speeds, so a portfolio slowly leaves its target mix.
Left alone, a "Balanced" portfolio can become much riskier after a long rise in shares. The two
common policies are:

- **Calendar rebalancing**: trade back to target every month, quarter or year, whatever the
  drift. Simple, but it trades (and in real life pays costs and taxes) even when the mix is
  almost on target.
- **Threshold (drift) rebalancing**: trade only when an asset class is more than a set distance
  from its target. Fewer trades, and trades happen when they matter.

The target itself moves over time in Cairn, because the glide path makes the mix safer as the
goal approaches.

## Decision

- Rebalance **when any asset class is more than 5 percentage points away from its target
  weight**, where the target is the glide-path allocation for the goal on that date.
- When a rebalance is due, bring **every** asset class back to its target (not just the one that
  drifted), using the largest-remainder split so the transfers are whole cents and sum exactly
  to zero.
- `domain/rebalancing.py` is a pure function from holdings and target weights to transfers.
  The service posts the transfers as one `rebalance` journal entry between holding accounts.
- Rebalancing is **idempotent per goal and date**: the idempotency key includes the date, so a
  retried or repeated request on the same day returns the first entry.

## Consequences

- Within the band, nothing happens: tests check that no transfers are produced when every class
  is within 5 points.
- After a rebalance, every weight is within one cent of its target, and the transfers balance;
  both are property-tested over random holdings.
- Rebalancing is not always kinder in a crash. In the stylised 2008 replay it can deepen the
  drawdown (it buys shares while they are still falling) while helping the recovery. The stress
  test shows both paths so the trade-off is visible rather than hidden.
- The drift that triggered a past rebalance is not stored, so explanations of old rebalances
  describe it relative to the threshold instead of quoting a figure.
