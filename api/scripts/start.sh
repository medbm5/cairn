#!/bin/sh
# Production start: migrate, seed the demo once (a no-op when goals exist), then serve.
set -e
alembic upgrade head
python scripts/seed.py --if-empty
exec uvicorn cairn.main:app --host 0.0.0.0 --port "${PORT:-8000}"
