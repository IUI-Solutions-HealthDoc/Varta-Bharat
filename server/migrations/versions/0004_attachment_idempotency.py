"""attachment idempotency key (invariant I6)

Revision ID: 0004
Revises: 0003

A retried POST /v1/attachments with the same X-Idempotency-Key returns the same attachment.
Rejected rows are excluded, so a retry after a rejection creates a new attachment.
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE attachments ADD COLUMN idempotency_key uuid")
    op.execute("""
    CREATE UNIQUE INDEX attachments_idempotency_key_uniq
      ON attachments (uploader_id, idempotency_key)
      WHERE idempotency_key IS NOT NULL AND state <> 'rejected'""")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS attachments_idempotency_key_uniq")
    op.execute("ALTER TABLE attachments DROP COLUMN IF EXISTS idempotency_key")