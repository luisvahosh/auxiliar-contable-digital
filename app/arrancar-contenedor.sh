#!/bin/sh
# Arranque del contenedor: migra, recolecta estáticos y sirve con gunicorn.
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 90
