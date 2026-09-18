web: daphne -b 0.0.0.0 -p $PORT kaamsetu.asgi:application
worker: celery -A kaamsetu worker --loglevel=info
beat: celery -A kaamsetu beat --loglevel=info
