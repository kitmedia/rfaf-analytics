web: uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
worker: celery -A backend.workers.tasks worker --loglevel=info --concurrency=4
beat: celery -A backend.workers.tasks beat --loglevel=info
flower: celery -A backend.workers.tasks flower --port=5555
