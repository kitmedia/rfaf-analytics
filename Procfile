web: bash backend/scripts/start.sh
worker: celery -A backend.workers.tasks worker --beat --loglevel=info --concurrency=4
