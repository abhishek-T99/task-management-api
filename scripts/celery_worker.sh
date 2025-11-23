#!/bin/bash

set -o errexit
set -o nounset

# Wait for Redis
echo "Waiting for Redis..."
redis_ready() {
    uv run python -c "
import redis
r = redis.Redis(host='redis', port=6379, socket_connect_timeout=1)
r.ping()
"
}

until redis_ready; do
  >&2 echo 'Redis not available, sleeping...'
  sleep 2
done
>&2 echo 'Redis is available!'

# Wait for PostgreSQL (if your tasks use DB)
echo "Waiting for PostgreSQL..."
POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}

while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 2
  echo "Waiting for database..."
done
echo "Connected to PostgreSQL!"

echo "Starting Celery worker..."
exec uv run celery -A config.celery:app worker --loglevel=info
