#!/bin/bash
# Production startup: run migrations then start uvicorn
set -e

echo "Running database migrations..."
alembic upgrade head || echo "WARNING: Alembic migration failed, continuing with create_tables fallback"

echo "Starting uvicorn..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
