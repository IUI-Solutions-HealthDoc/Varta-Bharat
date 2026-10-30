from logging.config import fileConfig

from alembic import context
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import create_engine, pool

from app.config import Settings

# Migration 0003 reads APP_DB_PASSWORD / ENVIRONMENT from os.environ, so export .env too.
load_dotenv(find_dotenv(usecwd=True))

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = None  # schema is managed with explicit SQL migrations


def get_url() -> str:
    # Fresh Settings() on purpose: tests set ALEMBIC_DATABASE_URL just before each run,
    # so the module-level singleton in app.config would be stale.
    s = Settings()
    url = s.alembic_database_url or s.database_url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if not url.startswith("postgresql+psycopg://"):
        from psycopg.conninfo import conninfo_to_dict
        from sqlalchemy import URL

        d = conninfo_to_dict(url)
        return URL.create(
            "postgresql+psycopg",
            username=d.get("user"),
            password=d.get("password"),
            host=d.get("host"),
            port=int(d["port"]) if d.get("port") else None,
            database=d.get("dbname"),
        ).render_as_string(hide_password=False)
    return url


def run_migrations_offline() -> None:
    context.configure(url=get_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
