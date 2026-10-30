"""Celery app. Run locally: uv run celery -A app.worker worker -l info"""

from urllib.parse import urlsplit, urlunsplit

from celery import Celery

from app.config import settings


def _broker_url() -> str:
    # Same Valkey as the app, database 1, so queue traffic stays apart from OTPs and tickets.
    return urlunsplit(urlsplit(settings.valkey_url)._replace(path="/1"))


celery_app = Celery("varta", broker=_broker_url(), include=["app.media.tasks"])
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_ignore_result=True,
)