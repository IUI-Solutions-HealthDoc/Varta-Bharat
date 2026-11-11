"""Block checks shared with the send path."""

from uuid import UUID

import psycopg


def blocked_between(conn: psycopg.Connection, user_a: UUID, user_b: UUID) -> bool:
    """True if either user has blocked the other. Call from send_message (DMs) and DM creation."""
    return conn.execute(
        "SELECT EXISTS (SELECT 1 FROM user_blocks "
        "WHERE (blocker_id = %s AND blocked_id = %s) OR (blocker_id = %s AND blocked_id = %s))",
        (user_a, user_b, user_b, user_a),
    ).fetchone()[0]