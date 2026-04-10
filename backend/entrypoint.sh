#!/bin/sh
set -e

if [ "${USE_POSTGRES}" = "1" ]; then
  python -c "import os, time, psycopg
for _ in range(30):
    try:
        psycopg.connect(
            dbname=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=os.getenv('POSTGRES_HOST', 'postgres'),
            port=os.getenv('POSTGRES_PORT', '5432'),
        ).close()
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit('Postgres is not ready')"
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn photo_tagging_api.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${DJANGO_GUNICORN_WORKERS:-3}" \
  --timeout "${DJANGO_GUNICORN_TIMEOUT:-120}"
