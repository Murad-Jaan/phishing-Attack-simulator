import os

from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "phishsim",
    broker=redis_url,
    backend=redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "dispatch-scheduled-campaigns": {
            "task": "campaigns.dispatch_due",
            "schedule": 30.0,
        },
        "run-data-retention": {
            "task": "retention.run_scheduled",
            "schedule": 86400.0,
        },
    },
)


@celery_app.task(name="ping")
def ping():
    return "pong"
