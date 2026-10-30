# Varta Bharat: backend

Foundation from Engineering Plan v2 (sections 7 and 8): schema, send path, local infra, CI.

## Run it

```bash
cp .env.example .env
make up        # Postgres 18, Valkey, MinIO
make migrate   # Alembic upgrade head
make test      # pytest (creates varta_test automatically)
make run       # API at http://localhost:8000/health
```

Requires Docker and [uv](https://docs.astral.sh/uv/). Run `uv sync` in `server/` once; commit the
generated `uv.lock`.

## Layout

- `server/app`: FastAPI app, config, JSON logging with redaction, `send.py` (plan section 7.2)
- `server/migrations`: Alembic migrations (0001 core, 0002 messaging); plain SQL, copied from plan section 8
- `server/tests`: schema constraints, migration up/down, send transaction (idempotency, 100 concurrent sends, no gaps)
- `infra/`: IaC goes here (staging with OPS-1)
- `.github/workflows/ci.yml`: lint, migration up/down/up, tests, gitleaks


#