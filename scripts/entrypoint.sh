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
python manage.py migrate

# Collect static files (only for production)
if [ "$DJANGO_DEBUG" = "False" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

echo "Starting Django server..."
exec python manage.py runserver
