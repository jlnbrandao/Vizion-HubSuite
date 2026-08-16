#!/bin/sh
set -e
echo "Running tracking migrations..."
alembic upgrade head
if [ "${RUN_SEED:-false}" = "true" ]; then
  PYTHONPATH="/app:/app/src" python -m scripts.seed || true
fi
echo "Starting tracking API..."
exec uvicorn tracking.main:app --host 0.0.0.0 --port 8000
