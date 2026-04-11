FROM python:3.11-slim
WORKDIR /app
COPY microservices/celery-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY microservices/celery-worker/worker.py .
CMD ["celery", "-A", "worker", "worker", "--loglevel=info", "--concurrency=4"]
