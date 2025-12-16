#!/usr/bin/env sh
set -eu

echo "Waiting for database..."
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-heritage_platform}"
export PGPASSWORD="${POSTGRES_PASSWORD:-postgres}"

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
  sleep 1
done

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static..."
python manage.py collectstatic --noinput

if [ "${CREATE_SUPERUSER:-true}" = "true" ]; then
  echo "Ensuring superuser exists..."
  python manage.py createsuperuser --noinput || true
fi

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  echo "Seeding demo data..."
  python manage.py seed_demo_data || true
fi

if [ "${SEED_HERITAGE_DATA:-true}" = "true" ]; then
  echo "Seeding heritage data..."
  seed_args=""
  if [ "${SEED_HERITAGE_RESET:-false}" = "true" ]; then
    seed_args="$seed_args --reset"
  fi
  if [ "${SEED_HERITAGE_SKIP_MEDIA_DOWNLOADS:-false}" = "true" ]; then
    seed_args="$seed_args --skip-media-downloads"
  fi

  if ! python manage.py seed_heritage $seed_args; then
    echo "WARNING: seed_heritage failed; continuing startup." >&2
  fi
fi

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"
