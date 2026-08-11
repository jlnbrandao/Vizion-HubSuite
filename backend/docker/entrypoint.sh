#!/bin/sh
set -e

echo "Running database migrations..."
# Prefer migrate role (BYPASSRLS / DDL); fall back to DATABASE_URL.
if [ -n "${DATABASE_MIGRATE_URL:-}" ]; then
  DATABASE_URL="$DATABASE_MIGRATE_URL" alembic upgrade head
else
  alembic upgrade head
fi

echo "Starting API..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
