.PHONY: up down migrate downgrade test lint run worker beat
up:
	docker compose up -d --wait postgres valkey minio
	docker compose run --rm minio-init
down:
	docker compose down
migrate:
	cd server && uv run alembic upgrade head
downgrade:
	cd server && uv run alembic downgrade -1
test:
	cd server && uv run pytest -v
lint:
	cd server && uv run ruff check .
run:
	cd server && uv run uvicorn app.main:app --reload
worker:
	cd server && uv run celery -A app.worker worker -l info
beat:
	cd server && uv run celery -A app.worker beat -l info -s .celerybeat-schedule
