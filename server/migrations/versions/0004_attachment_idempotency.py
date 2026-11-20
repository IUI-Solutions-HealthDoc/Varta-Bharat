"""attachment idempotency key (invariant I6) and sweep bookkeeping

Revision ID: 0004
Revises: 0003

A retried POST /v1/attachments with the same X-Idempotency-Key returns the same attachment.
The key is scoped to (tenant, uploader), so a user in two tenants can reuse a key in each.
Rejected rows are excluded, so a retry after a rejection creates a new attachment.
last_swept_at lets the pending-attachment sweep rotate through rows instead of rechecking
the same ones every minute.
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE attachments ADD COLUMN idempotency_key uuid")
    op.execute("ALTER TABLE attachments ADD COLUMN last_swept_at timestamptz")
    op.execute("""
    CREATE UNIQUE INDEX attachments_idempotency_key_uniq
      ON attachments (tenant_id, uploader_id, idempotency_key)
      WHERE idempotency_key IS NOT NULL AND state <> 'rejected'""")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS attachments_idempotency_key_uniq")
    op.execute("ALTER TABLE attachments DROP COLUMN IF EXISTS last_swept_at")
    op.execute("ALTER TABLE attachments DROP COLUMN IF EXISTS idempotency_key")
