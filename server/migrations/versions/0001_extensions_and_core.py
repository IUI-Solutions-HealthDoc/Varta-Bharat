"""extensions, tenants, users, conversations (plan v2, section 8)

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")  # stretch: search

    op.execute("""
    CREATE TABLE tenants (
      id             uuid PRIMARY KEY DEFAULT uuidv7(),
      slug           text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{3,40}$'),
      name           text NOT NULL,
      retention_days integer CHECK (retention_days IS NULL OR retention_days > 0),
      created_at     timestamptz NOT NULL DEFAULT now()
    )""")

    op.execute("""
    CREATE TABLE users (
      id            uuid PRIMARY KEY DEFAULT uuidv7(),
      email         citext UNIQUE,
      phone_enc     bytea,
      phone_lookup  bytea UNIQUE,
      display_name  text NOT NULL CHECK (length(display_name) BETWEEN 1 AND 80),
      avatar_key    text,
      status        text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','deleted')),
      created_at    timestamptz NOT NULL DEFAULT now(),
      deleted_at    timestamptz
    )""")

    op.execute("""
    CREATE TABLE tenant_members (
      tenant_id    uuid NOT NULL REFERENCES tenants(id),
      user_id      uuid NOT NULL REFERENCES users(id),
      role         text NOT NULL CHECK (role IN ('owner','admin','moderator','member','guest')),
      employee_id  text,
      joined_at    timestamptz NOT NULL DEFAULT now(),
      removed_at   timestamptz,
      PRIMARY KEY (tenant_id, user_id)
    )""")

    op.execute("""
    CREATE TABLE communities (
      id          uuid PRIMARY KEY DEFAULT uuidv7(),
      tenant_id   uuid NOT NULL REFERENCES tenants(id),
      name        text NOT NULL,
      created_by  uuid NOT NULL REFERENCES users(id),
      created_at  timestamptz NOT NULL DEFAULT now()
    )""")

    op.execute("""
    CREATE TABLE conversations (
      id            uuid PRIMARY KEY DEFAULT uuidv7(),
      tenant_id     uuid NOT NULL REFERENCES tenants(id),
      community_id  uuid REFERENCES communities(id),
      kind          text NOT NULL CHECK (kind IN ('dm','private','public','announcement')),
      title         text,
      dm_key        text UNIQUE,
      last_seq      bigint NOT NULL DEFAULT 0,
      created_by    uuid NOT NULL REFERENCES users(id),
      created_at    timestamptz NOT NULL DEFAULT now(),
      CHECK ((kind = 'dm') = (dm_key IS NOT NULL)),
      CHECK (kind <> 'dm' OR community_id IS NULL)
    )""")

    op.execute("""
    CREATE TABLE conversation_members (
      conversation_id   uuid NOT NULL REFERENCES conversations(id),
      user_id           uuid NOT NULL REFERENCES users(id),
      role              text NOT NULL DEFAULT 'member' CHECK (role IN ('admin','member')),
      visible_from_seq  bigint NOT NULL DEFAULT 1,
      delivered_seq     bigint NOT NULL DEFAULT 0,
      read_seq          bigint NOT NULL DEFAULT 0,
      muted_until       timestamptz,
      left_at           timestamptz,
      PRIMARY KEY (conversation_id, user_id),
      CHECK (read_seq <= delivered_seq)
    )""")
    op.execute(
        "CREATE INDEX conversation_members_user_active "
        "ON conversation_members (user_id) WHERE left_at IS NULL"
    )


def downgrade() -> None:
    for t in (
        "conversation_members",
        "conversations",
        "communities",
        "tenant_members",
        "users",
        "tenants",
    ):
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS citext")
