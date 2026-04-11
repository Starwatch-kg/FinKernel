FROM python:3.11-slim
WORKDIR /app
COPY microservices/shared /app/shared
COPY microservices/ai-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY microservices/ai-service/ .
CMD ["uvicorn", "main_secure:app", "--host", "0.0.0.0", "--port", "8002"]
