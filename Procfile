web: daphne -b 0.0.0.0 -p $PORT workersgrid.asgi:application
worker: celery -A workersgrid worker --loglevel=info
beat: celery -A workersgrid beat --loglevel=info
