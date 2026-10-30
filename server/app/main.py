from contextlib import asynccontextmanager
import logging

import psycopg
from fastapi import FastAPI, HTTPException

from app.config import settings
from app.logging_setup import setup_logging
from app.messaging import router as messaging_router
from app.ws import router as ws_router

setup_logging()
log = logging.getLogger("varta")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment != "local":
        raise RuntimeError(
            f"Refusing to start with dev authentication stub in environment '{settings.environment}'. "
            "Real auth (BE-2) is required outside ENVIRONMENT=local."
        )
    try:
        await ws_router.ensure_valkey_subscriber()
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not start Valkey subscriber at lifespan startup: %s", exc)
    try:
        yield
    finally:
        await ws_router.stop_valkey_subscriber()


app = FastAPI(title="Varta Bharat API", version="0.1.0", lifespan=lifespan)
app.include_router(messaging_router)
app.include_router(ws_router)


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
