#!/bin/sh
set -eu

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000
