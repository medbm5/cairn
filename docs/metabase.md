# Metabase on the demo data

Metabase runs next to the API in Docker Compose, for quick analytics on the demo database.

## Start it

```bash
docker compose -f infra/docker-compose.yml up -d db metabase
cd api && uv run alembic upgrade head && uv run python scripts/seed.py   # demo data
```

Open <http://localhost:3000> (or `METABASE_PORT` if you changed it), create the local admin
account Metabase asks for, then add a database:

| Setting | Value |
|---|---|
| Database type | PostgreSQL |
| Host | `db` (the Compose service name) |
| Port | `5432` |
| Database name | `cairn` |
| Username / password | `cairn` / `cairn` (local only) |

Metabase keeps its own settings in the `metabase-data` volume, so this is done once.

## Three questions

Create each one with **New → SQL query**, then save it to a "Cairn" collection. Money is stored
as integer cents; the queries convert to euros only for display.

### 1. Assets per goal type

What the demo holds, by kind of goal. Visualise as a bar chart.

```sql
SELECT g.type AS goal_type,
       ROUND(SUM(a.balance_cents) / 100.0, 2) AS assets_eur
FROM accounts a
JOIN goals g ON g.id = a.goal_id
WHERE a.kind LIKE 'holding:%'
GROUP BY g.type
ORDER BY assets_eur DESC;
```

### 2. Rebalancing events per month

How often drift went past the 5-point threshold. Visualise as a line or bar chart by month.

```sql
SELECT date_trunc('month', created_at)::date AS month,
       COUNT(*) AS rebalances
FROM journal_entries
WHERE kind = 'rebalance'
GROUP BY 1
ORDER BY 1;
```

### 3. Reconciliation status

The same checks as `GET /ledger/reconciliation`, as numbers. All three must be zero; set up a
Metabase alert on this question to be told if one is not.

```sql
SELECT
  (SELECT COUNT(*) FROM (
     SELECT entry_id FROM journal_lines
     GROUP BY entry_id HAVING SUM(amount_cents) <> 0
   ) unbalanced) AS unbalanced_entries,
  (SELECT COUNT(*)
     FROM accounts a
     LEFT JOIN (
       SELECT account_id, SUM(amount_cents) AS total
       FROM journal_lines GROUP BY account_id
     ) l ON l.account_id = a.id
     WHERE a.balance_cents <> COALESCE(l.total, 0)) AS mismatched_accounts,
  (SELECT COALESCE(SUM(amount_cents), 0) FROM journal_lines) AS ledger_total_cents;
```

Put the three on one dashboard ("Cairn overview"). On freshly seeded data, the reconciliation
card reads 0, 0, 0.
