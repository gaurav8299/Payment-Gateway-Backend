#!/bin/bash
set -e

echo "Waiting for PostgreSQL database to be ready..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "PostgreSQL is ready!"

echo "Applying database migrations..."
python manage.py makemigrations accounts merchant customer orders payments refunds wallet notifications audit_logs webhooks common --noinput || true
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

exec "$@"
