release: python manage.py migrate --no-input && python manage.py collectstatic --no-input
web: DJANGO_SETTINGS_MODULE=pos.settings gunicorn pos.wsgi