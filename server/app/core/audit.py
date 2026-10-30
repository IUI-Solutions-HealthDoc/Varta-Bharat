"""Audit trail writer (audit_log is append-only for the app role).

audit() runs on the connection it is given, so the entry commits or rolls back together
with the action it records. Never put message bodies, tokens, OTPs or tickets in `target`.
"""

from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb


def audit(
    conn: psycopg.Connection,
    tenant_id: UUID,
    actor_id: UUID | None,
    action: str,
    target: dict[str, Any],
    ip: str | None = None,
) -> int:
    row = conn.execute(
        "INSERT INTO audit_log (tenant_id, actor_id, action, target, ip) "
        "VALUES (%s, %s, %s, %s, %s::inet) RETURNING id",
        (tenant_id, actor_id, action, Jsonb(target), ip),
    ).fetchone()
    return row[0]
