"""attachments, messages, invitations, devices, audit, moderation (plan v2, section 8)

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE attachments (
      id           uuid PRIMARY KEY DEFAULT uuidv7(),
      tenant_id    uuid NOT NULL REFERENCES tenants(id),
      uploader_id  uuid NOT NULL REFERENCES users(id),
      object_key   text NOT NULL UNIQUE,
      mime         text NOT NULL,
      byte_size    bigint NOT NULL CHECK (byte_size > 0 AND byte_size <= 33554432),
      sha256       bytea,
      width        integer,
      height       integer,
      duration_ms  integer,
      state        text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','ready','rejected')),
      created_at   timestamptz NOT NULL DEFAULT now()
    )""")

    op.execute("""
    CREATE TABLE messages (
      conversation_id  uuid NOT NULL REFERENCES conversations(id),
      seq              bigint NOT NULL,
      id               uuid NOT NULL DEFAULT uuidv7(),
      sender_id        uuid NOT NULL REFERENCES users(id),
      client_msg_id    uuid NOT NULL,
      kind             text NOT NULL CHECK (kind IN ('text','media','system','delete','edit')),
      target_seq       bigint,
      body             text CHECK (length(body) <= 8000),
      attachment_id    uuid REFERENCES attachments(id),
      enc_scheme       smallint NOT NULL DEFAULT 0,
      created_at       timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY (conversation_id, seq),
      UNIQUE (id),
      UNIQUE (conversation_id, sender_id, client_msg_id),
      CHECK ((kind IN ('delete','edit')) = (target_seq IS NOT NULL))
    )""")

    op.execute("""
    CREATE TABLE invitations (
      id               uuid PRIMARY KEY DEFAULT uuidv7(),
      tenant_id        uuid NOT NULL REFERENCES tenants(id),
      conversation_id  uuid REFERENCES conversations(id),
      token_hash       bytea NOT NULL UNIQUE,
      grants_role      text NOT NULL DEFAULT 'member' CHECK (grants_role IN ('member','guest')),
      email_domain     citext,
      max_uses         integer CHECK (max_uses IS NULL OR max_uses > 0),
      used_count       integer NOT NULL DEFAULT 0,
      expires_at       timestamptz NOT NULL,
      revoked_at       timestamptz,
      created_by       uuid NOT NULL REFERENCES users(id),
      created_at       timestamptz NOT NULL DEFAULT now(),
      CHECK (max_uses IS NULL OR used_count <= max_uses)
    )""")

    op.execute("""
    CREATE TABLE contact_nicknames (
      owner_id   uuid NOT NULL REFERENCES users(id),
      target_id  uuid NOT NULL REFERENCES users(id),
      nickname   text NOT NULL CHECK (length(nickname) BETWEEN 1 AND 80),
      PRIMARY KEY (owner_id, target_id),
      CHECK (owner_id <> target_id)
    )""")

    op.execute("""
    CREATE TABLE user_blocks (
      blocker_id  uuid NOT NULL REFERENCES users(id),
      blocked_id  uuid NOT NULL REFERENCES users(id),
      created_at  timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY (blocker_id, blocked_id)
    )""")

    op.execute("""
    CREATE TABLE reports (
      id               uuid PRIMARY KEY DEFAULT uuidv7(),
      tenant_id        uuid NOT NULL REFERENCES tenants(id),
      reporter_id      uuid NOT NULL REFERENCES users(id),
      conversation_id  uuid NOT NULL,
      seq              bigint NOT NULL,
      reason           text NOT NULL,
      status           text NOT NULL DEFAULT 'open' CHECK (status IN ('open','actioned','dismissed')),
      created_at       timestamptz NOT NULL DEFAULT now(),
      FOREIGN KEY (conversation_id, seq) REFERENCES messages (conversation_id, seq)
    )""")

    op.execute("""
    CREATE TABLE devices (
      id              uuid PRIMARY KEY DEFAULT uuidv7(),
      user_id         uuid NOT NULL REFERENCES users(id),
      platform        text NOT NULL CHECK (platform IN ('ios','android','web','desktop')),
      push_token      text,
      refresh_hash    bytea NOT NULL,
      refresh_family  uuid NOT NULL,
      last_seen_at    timestamptz NOT NULL DEFAULT now(),
      revoked_at      timestamptz
    )""")

    op.execute("""
    CREATE TABLE audit_log (
      id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      tenant_id  uuid NOT NULL,
      actor_id   uuid,
      action     text NOT NULL,
      target     jsonb NOT NULL,
      ip         inet,
      at         timestamptz NOT NULL DEFAULT now()
    )""")

    # Application role: full access to normal tables, INSERT + SELECT only on audit_log.
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'varta_app') THEN
        CREATE ROLE varta_app NOLOGIN;
      END IF;
    END $$""")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO varta_app")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM varta_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO varta_app")


def downgrade() -> None:
    for t in (
        "audit_log",
        "devices",
        "reports",
        "user_blocks",
        "contact_nicknames",
        "invitations",
        "messages",
        "attachments",
    ):
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
