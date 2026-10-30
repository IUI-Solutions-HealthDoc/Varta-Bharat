# Varta Bharat

Monorepo for Engineering Plan v2 (section 6): pnpm + Turborepo for TypeScript, `uv` for Python.

## Run it

```bash
cp .env.example .env
make up        # Postgres 18, Valkey, MinIO
make migrate   # Alembic upgrade head
make test      # pytest (creates varta_test automatically)
make run       # API at http://localhost:8000/health
```

Requires Docker and [uv](https://docs.astral.sh/uv/). Run `uv sync` in `server/` once.

TypeScript workspaces need Node 22+ and pnpm 10: run `pnpm install` at the repo root.

## Layout

- `server/app`: FastAPI app, config, JSON logging with redaction, `send.py` (plan section 7.2)
- `server/migrations`: Alembic migrations (0001 core, 0002 messaging); plain SQL, copied from plan section 8
- `server/tests`: schema constraints, migration up/down, send transaction (idempotency, 100 concurrent sends, no gaps)
- `server/scripts/export_openapi.py`: writes the OpenAPI document that `packages/protocol` is generated from
- `apps/mobile`: Expo app for Android and iOS (MOB team)
- `apps/web`: Next.js App Router web app and admin console (WEB-1)
- `apps/desktop`: Electron shell that loads the hosted web app (WEB-2)
- `packages/protocol`: TS types generated from the server's OpenAPI and WS JSON Schema
- `packages/sync`: shared sync engine (outbox, cursors, gap repair; plan section 7.4)
- `infra/`: IaC, k6 load scripts, Toxiproxy scenarios (OPS-1)
- `docs/threat-model/`: STRIDE threat model (plan section 9.1)
- `.github/workflows/ci.yml`: lint, migration up/down/up, tests, gitleaks


#