FROM python:3.11-slim

WORKDIR /app

# System deps for mplsoccer/matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libffi-dev ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Non-root user for security
RUN useradd -m -r appuser && chown -R appuser:appuser /app
COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 8000

CMD ["bash", "backend/scripts/start.sh"]
