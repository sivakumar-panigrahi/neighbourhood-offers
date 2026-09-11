#!/bin/sh
set -e

echo "==> Running database migrations..."
alembic upgrade head

if [ "$SEED_DEMO_DATA" = "true" ] || [ "$AUTO_SEED" = "true" ]; then
    echo "==> Seeding initial demo data (idempotent)..."
    python -m scripts.seed
fi

echo "==> Starting FastAPI server on 0.0.0.0:${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
