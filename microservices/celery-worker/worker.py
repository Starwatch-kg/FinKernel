"""Celery Worker"""

import json
import os

import httpx
import redis
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
AI_URL = os.getenv("AI_URL", "http://ai:8002")

celery_app = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="process_transaction", bind=True, max_retries=3)
def process_transaction(self, event_data: dict):
    try:
        user_id = event_data.get("user_id")
        response = httpx.post(f"{AI_URL}/predict/{user_id}", timeout=10.0)
        response.raise_for_status()
        return {"status": "success", "user_id": user_id}
    except httpx.HTTPError as e:
        raise self.retry(exc=e, countdown=2**self.request.retries)


def listen_events():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe("transaction.created")

    print("🎧 Event listener started")

    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                event_data = json.loads(message["data"])
                process_transaction.delay(event_data)
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    listen_events()
