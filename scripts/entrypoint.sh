#!/bin/sh

set -e

echo "Waiting for PostgreSQL..."

POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}

while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 1
  echo "Waiting for database..."
done

echo "Connected to PostgreSQL!"

# Apply database migrations
echo "Applying database migrations..."
uv run python manage.py migrate

# Create superuser if environment variables are set
if [ -n "${SUPERUSER_EMAIL:-}" ] && [ -n "${SUPERUSER_PASSWORD:-}" ]; then
    echo "Setting up superuser..."
    sh /app/scripts/create_superuser.sh
else
    echo "Superuser environment variables not set. Skipping superuser creation."
fi

# Collect static files (only for production)
if [ "$DJANGO_DEBUG" = "False" ]; then
  echo "Collecting static files..."
  uv run python manage.py collectstatic --noinput
fi

echo "Starting Django server..."
exec uv run python manage.py runserver 0.0.0.0:8000
