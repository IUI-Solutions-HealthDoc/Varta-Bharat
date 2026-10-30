import os
import uuid
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

load_dotenv(find_dotenv(usecwd=True))

ROOT = Path(__file__).resolve().parents[1]
TEST_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://varta:varta@localhost:5432/varta_test")


def ensure_db(url: str, drop: bool = False) -> None:
    info = conninfo_to_dict(url)
    name = info["dbname"]
    info["dbname"] = "postgres"
    with psycopg.connect(make_conninfo(**info), autocommit=True) as c:
        if drop:
            c.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
        if not c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
            c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def alembic_cfg(url: str) -> Config:
    os.environ["ALEMBIC_DATABASE_URL"] = url
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    return cfg


def upgrade(url: str, rev: str = "head") -> None:
    command.upgrade(alembic_cfg(url), rev)


def downgrade(url: str, rev: str = "base") -> None:
    command.downgrade(alembic_cfg(url), rev)


def seed_chat(conn: psycopg.Connection, conv_kind: str = "private") -> dict:
    """Tenant with alice (conversation admin) and bob (member) in one conversation."""
    suffix = uuid.uuid4().hex[:8]
    tenant = conn.execute(
        "INSERT INTO tenants (slug, name) VALUES (%s, 'RCM') RETURNING id", (f"rcm-{suffix}",)
    ).fetchone()[0]
    ids = {}
    for name in ("alice", "bob", "carol"):
        uid = conn.execute(
            "INSERT INTO users (email, display_name) VALUES (%s, %s) RETURNING id",
            (f"{name}-{suffix}@example.com", name.title()),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO tenant_members (tenant_id, user_id, role) VALUES (%s, %s, 'member')",
            (tenant, uid),
        )
        ids[name] = uid
    conv = conn.execute(
        "INSERT INTO conversations (tenant_id, kind, title, created_by) "
        "VALUES (%s, %s, 'general', %s) RETURNING id",
        (tenant, conv_kind, ids["alice"]),
    ).fetchone()[0]
    for name, role in (("alice", "admin"), ("bob", "member")):
        conn.execute(
            "INSERT INTO conversation_members (conversation_id, user_id, role) VALUES (%s, %s, %s)",
            (conv, ids[name], role),
        )
    conn.commit()
    return {"tenant": tenant, "conv": conv, **ids}
