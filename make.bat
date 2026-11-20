@echo off
setlocal

set TARGET=%1
if "%TARGET%"=="" set TARGET=help

if "%TARGET%"=="up" (
    docker compose up -d --wait postgres valkey minio
    docker compose run --rm minio-init
) else if "%TARGET%"=="down" (
    docker compose down
) else if "%TARGET%"=="migrate" (
    cd server && uv run alembic upgrade head
) else if "%TARGET%"=="downgrade" (
    cd server && uv run alembic downgrade -1
) else if "%TARGET%"=="test" (
    cd server && uv run pytest -v
) else if "%TARGET%"=="lint" (
    cd server && uv run ruff check .
) else if "%TARGET%"=="run" (
    cd server && uv run uvicorn app.main:app --reload
) else if "%TARGET%"=="worker" (
    rem Celery's default prefork pool does not run on Windows
    cd server && uv run celery -A app.worker worker -l info --pool=solo
) else if "%TARGET%"=="beat" (
    cd server && uv run celery -A app.worker beat -l info -s .celerybeat-schedule
) else (
    echo Usage: make [up^|down^|migrate^|downgrade^|test^|lint^|run^|worker^|beat]
)
