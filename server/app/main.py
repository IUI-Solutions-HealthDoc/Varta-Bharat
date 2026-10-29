import logging

import psycopg
from fastapi import FastAPI, HTTPException

from app.config import settings
from app.logging_setup import setup_logging

setup_logging()
log = logging.getLogger("varta")

app = FastAPI(title="Varta Bharat API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        log.error("readiness check failed", extra={"ctx": {"error": type(exc).__name__}})
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready"}
