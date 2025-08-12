release: DJANGO_SETTINGS_MODULE=pos.settings python manage.py migrate
web: pos.settings gunicorn pos.wsgi --log-file -