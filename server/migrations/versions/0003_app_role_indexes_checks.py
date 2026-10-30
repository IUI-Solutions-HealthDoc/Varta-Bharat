"""app login role, default privileges, user_id indexes, message CHECKs

Revision ID: 0003
Revises: 0002

The app connects as varta_api (member of varta_app), not as the table owner, so the
append-only audit_log is enforced. Migrations keep using the owner via ALEMBIC_DATABASE_URL.
Roles are cluster-wide, so downgrade leaves varta_api in place (same as varta_app in 0002).
"""
import os
import re

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _app_password() -> str:
    pw = os.environ.get("APP_DB_PASSWORD")
    if not pw:
        if os.environ.get("ENVIRONMENT", "local") != "local":
            raise RuntimeError("Set APP_DB_PASSWORD to create the varta_api login role")
        pw = "varta_api"  # local development only
    if not re.fullmatch(r"[A-Za-z0-9_.\-]+", pw):
        raise RuntimeError("APP_DB_PASSWORD may only contain letters, digits, _ . -")
    return pw


def upgrade() -> None:
    # 1. Login role for the app.
    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'varta_api') THEN
        CREATE ROLE varta_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
      END IF;
    END $$""")
    op.execute(f"ALTER ROLE varta_api PASSWORD '{_app_password()}'")
    op.execute("GRANT varta_app TO varta_api")

    # 2. Tables and sequences created later get the right grants automatically.
    op.execute("""
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO varta_app""")
    op.execute("""
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
      GRANT USAGE, SELECT ON SEQUENCES TO varta_app""")

    # 3. Indexes for per-user lookups.
    op.execute("CREATE INDEX tenant_members_user_id_idx ON tenant_members (user_id)")
    op.execute("CREATE INDEX devices_user_id_idx ON devices (user_id)")

    # 4. A text message needs a body, a media message needs an attachment.
    op.execute("""
    ALTER TABLE messages ADD CONSTRAINT messages_text_has_body
      CHECK (kind <> 'text' OR body IS NOT NULL)""")
    op.execute("""
    ALTER TABLE messages ADD CONSTRAINT messages_media_has_attachment
      CHECK (kind <> 'media' OR attachment_id IS NOT NULL)""")


def downgrade() -> None:
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_media_has_attachment")
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_text_has_body")
    op.execute("DROP INDEX IF EXISTS devices_user_id_idx")
    op.execute("DROP INDEX IF EXISTS tenant_members_user_id_idx")
    op.execute("""
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
      REVOKE USAGE, SELECT ON SEQUENCES FROM varta_app""")
    op.execute("""
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
      REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM varta_app""")
    op.execute("REVOKE varta_app FROM varta_api")
