# 0001 Integer cents and a double-entry ledger

- Status: accepted
- Date: 2026-10-24

## Context

Cairn records deposits, fees, market movements and rebalances for each goal, and shows balances
that people read as "my money". Two classic sources of error threaten that:

- **Floating-point money.** `0.1 + 0.2 != 0.3`. Splitting a deposit across four asset classes,
  or applying monthly returns, quickly produces fractions of a cent that drift over time.
- **Single-entry balances.** Updating a balance column in place leaves no trail, and nothing
  proves that money did not appear or disappear when a bug or a retry hits.

## Decision

1. **All money is stored and moved as integer cents** (`BIGINT` columns, `int` in Python,
   `number` cents in the API). Floats are allowed only inside the simulation engine, whose
   outputs are rounded to cents at the boundary.
2. **Splitting uses the largest-remainder method** (`domain/money.py`): the parts always sum to
   the exact total, and ties are broken in a fixed order so results are deterministic.
3. **Every movement is a journal entry whose lines sum to zero.** Accounts per goal are
   `external_bank`, `cash`, `fees`, `market` and one `holding:<asset_class>` per asset class.
   A deposit moves money from `external_bank` (negative) into holdings (positive); a market
   gain moves value from `market` into holdings; a rebalance moves value between holdings.
   `post_entry` refuses any entry that does not balance, inside one transaction.
4. **Account balances are stored for speed and checked by reconciliation.** Each posting updates
   `balance_cents` with an SQL-side increment (no lost updates). `GET /ledger/reconciliation`
   verifies that every entry balances, that every stored balance equals the sum of its lines,
   and that all lines sum to zero.
5. **Postings are idempotent.** Every entry has a unique `idempotency_key`; deposits require an
   `Idempotency-Key` header, and a repeated key returns the original entry instead of booking
   the money twice (including when two requests race: the unique constraint decides).

## Consequences

- Property-based tests generate random sequences of deposits and fees and check, after each
  one, that the ledger reconciles and the global sum is zero.
- Balances are explainable line by line, which is also what Pebble explains to the user.
- A `market` account is needed so that revaluations stay double-entry; it is not in the
  original list of account kinds but follows the same rule.
- Deleting a goal deletes its entries and accounts together; because each entry balances on its
  own, the remaining ledger still reconciles.
