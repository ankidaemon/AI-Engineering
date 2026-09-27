"""
The Celery application (§7.2).

Redis is the message broker: the queue of jobs waiting to be picked up. The
web process puts jobs in, the workers take jobs out, and the two never talk
to each other directly — they just share the queue. Start a worker with:

    celery -A src.workers.celery_app.app worker --loglevel=info

and scale by starting more of them (docker compose up --scale worker=4).
"""
from celery import Celery

from src.config import settings

app = Celery(
    "banking_assistant",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # A worker takes one job at a time; long embedding jobs should not let
    # one worker hoard the queue while others sit idle (§7.5).
    worker_prefetch_multiplier=1,
    task_acks_late=True,          # a job survives a worker crash (Failure 4)
)

app.autodiscover_tasks(["src.workers"])
