# Deploying Cairn

The API and its database run on **Render** (from `render.yaml`); the web app runs on **Vercel**
(from `web/vercel.json`). Both deploy from the GitHub repository.

> **Check the free tiers first.** Render's and Vercel's free plans change over time. Before you
> rely on them, check Render's current limits for free web services (instances spin down when
> idle, which is why Pebble shows a "waking up" message) and for free PostgreSQL databases
> (which may expire after a fixed period), and Vercel's limits for hobby projects.

## 1. API and database on Render

1. Push the repository to GitHub.
2. In Render, choose **New → Blueprint**, select the repository, and let Render read
   `render.yaml`. It creates:
   - `cairn-db`, a managed PostgreSQL database;
   - `cairn-api`, a Docker web service built from `api/Dockerfile`, with `/health` as its
     health check.
3. Render asks for the values marked `sync: false`:

   | Variable | Value |
   |---|---|
   | `CORS_ORIGINS` | Your Vercel domain and local development, comma-separated: `https://<your-app>.vercel.app,http://localhost:5173`. Only these origins can call the API. |
   | `OPENAI_API_KEY` | Optional. Without it, explanations use the written templates. |
   | `SENTRY_DSN` | Optional. Without it, error reporting is off. |

   `DATABASE_URL` is filled in from the database automatically (the app converts Render's
   `postgres://` URL to the psycopg driver). `RENDER_GIT_COMMIT` becomes the Sentry release.
4. Apply the blueprint. Each start runs, in order: `alembic upgrade head`, then
   `python scripts/seed.py --if-empty` (seeds the demo goals only when there are none), then
   the server on Render's `$PORT`.
5. Check it: `https://<your-api>.onrender.com/health` returns `{"status": "ok", ...}` and
   `https://<your-api>.onrender.com/ledger/reconciliation` returns `"ok": true`.

To reset the demo data, connect to the database (Render shows a `psql` command), delete the rows
from `journal_lines`, `journal_entries`, `accounts` and `goals`, then restart the service: the
seed runs again because no goals exist.

## 2. Web app on Vercel

1. In Vercel, **Add New → Project**, import the repository, and set the **Root Directory** to
   `web`. Vercel detects Vite; `web/vercel.json` sets the build command, the `dist` output, the
   SPA rewrite (every path serves `index.html`, so `/goals/3` works on reload) and long caching
   for hashed assets.
2. Environment variables (Production, and Preview if you use it):

   | Variable | Value |
   |---|---|
   | `VITE_API_URL` | The Render API URL, e.g. `https://<your-api>.onrender.com` (no trailing slash). It is read at build time, so redeploy after changing it. |
   | `VITE_SENTRY_DSN` | Optional, for the browser. |
   | `VITE_RELEASE` | Optional, e.g. `$VERCEL_GIT_COMMIT_SHA`, to tag Sentry events. |

3. Deploy, then add the resulting domain to the API's `CORS_ORIGINS` on Render if it differs
   from what you entered.

## 3. After deploying

- Open the site on a phone. On the first visit after the API has been idle, Pebble sleeps with
  "The demo server is waking up" and stretches when the API answers.
- Remove `OPENAI_API_KEY` and reload a page with explanations: they still appear, from the
  templates (`"source": "fallback"` in the `/explain` response).
- Turn on **Quiet Pebble**: Pebble disappears and explanations show as plain panels.

## Kubernetes (optional)

`infra/k8s/` holds a Deployment (with a migration init container, readiness and liveness probes
on `/health`, and resource requests), a Service, a ConfigMap and a Secret template. Build and
push the API image, set its name in `deployment.yaml`, create the Secret from
`secret.example.yaml`, then `kubectl apply -k infra/k8s`.
