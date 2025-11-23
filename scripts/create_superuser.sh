#!/bin/bash

set -o errexit
set -o nounset

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}

while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 1
  echo "Waiting for database..."
done

echo "Connected to PostgreSQL!"

# Check if superuser already exists
echo "Checking if superuser already exists..."
if uv run python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if User.objects.filter(email='$SUPERUSER_EMAIL').exists():
    print('Superuser already exists. Skipping creation.')
    exit(0)
else:
    print('Superuser does not exist. Will create.')
    exit(1)
" > /dev/null 2>&1; then
    echo "Superuser creation skipped - already exists."
    exit 0
fi

# Create superuser
echo "Creating superuser..."
uv run python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()

# Check again to avoid race conditions
if User.objects.filter(email='$SUPERUSER_EMAIL').exists():
    print('Superuser already exists (double-check).')
else:
    print('Creating superuser...')
    try:
        User.objects.create_superuser(
            email='$SUPERUSER_EMAIL',
            password='$SUPERUSER_PASSWORD',
            username='$SUPERUSER_USERNAME'
        )
        print('Superuser created successfully!')
    except Exception as e:
        print(f'Error creating superuser: {e}')
"
