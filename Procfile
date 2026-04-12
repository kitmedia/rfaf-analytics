web: bash backend/scripts/start.sh
worker: celery -A backend.workers.tasks worker --loglevel=info --concurrency=4
beat: celery -A backend.workers.tasks beat --loglevel=info
flower: celery -A backend.workers.tasks flower --port=5555
