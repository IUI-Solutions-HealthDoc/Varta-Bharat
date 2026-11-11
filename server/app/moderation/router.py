"""Block and report (Apple guideline 1.2). Report text is never logged."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.audit import audit
from app.core.db import get_conn
from app.media.deps import AuthUser, current_user

router = APIRouter(prefix="/v1", tags=["moderation"])


class BlockRequest(BaseModel):
    user_id: UUID


class BlockedUser(BaseModel):
    id: UUID
    display_name: str


class ReportRequest(BaseModel):
    conversation_id: UUID
    seq: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason required")
        return value


class ReportOut(BaseModel):
    id: UUID
    status: str


@router.post("/blocks", status_code=204)
def block_user(body: BlockRequest, user: Annotated[AuthUser, Depends(current_user)]) -> None:
    if body.user_id == user.id:
        raise HTTPException(status_code=422, detail="cannot block yourself")
    with get_conn() as conn:
        member = conn.execute(
            "SELECT 1 FROM tenant_members "
            "WHERE tenant_id = %s AND user_id = %s AND removed_at IS NULL",
            (user.tenant_id, body.user_id),
        ).fetchone()
        if member is None:  # unknown user and other tenant's user look the same
            raise HTTPException(status_code=404, detail="user not found")
        conn.execute(
            "INSERT INTO user_blocks (blocker_id, blocked_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (user.id, body.user_id),
        )


@router.get("/blocks", response_model=list[BlockedUser])
def list_blocks(user: Annotated[AuthUser, Depends(current_user)]) -> list[BlockedUser]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT u.id, u.display_name FROM user_blocks b "
            "JOIN users u ON u.id = b.blocked_id "
            "JOIN tenant_members tm ON tm.user_id = u.id AND tm.tenant_id = %s "
            "AND tm.removed_at IS NULL "
            "WHERE b.blocker_id = %s ORDER BY b.created_at",
            (user.tenant_id, user.id),
        ).fetchall()
    return [BlockedUser(id=r[0], display_name=r[1]) for r in rows]


@router.delete("/blocks/{user_id}", status_code=204)
def unblock_user(user_id: UUID, user: Annotated[AuthUser, Depends(current_user)]) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM user_blocks WHERE blocker_id = %s AND blocked_id = %s",
            (user.id, user_id),
        )


@router.post("/reports", response_model=ReportOut, status_code=201)
def report_message(
    body: ReportRequest, user: Annotated[AuthUser, Depends(current_user)]
) -> ReportOut:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT m.sender_id FROM messages m "
            "JOIN conversations c ON c.id = m.conversation_id "
            "JOIN conversation_members cm ON cm.conversation_id = c.id "
            "AND cm.user_id = %s AND cm.left_at IS NULL "
            "WHERE m.conversation_id = %s AND m.seq = %s AND c.tenant_id = %s",
            (user.id, body.conversation_id, body.seq, user.tenant_id),
        ).fetchone()
        if row is None:  # unknown message and not-a-member look the same
            raise HTTPException(status_code=404, detail="message not found")
        if row[0] == user.id:
            raise HTTPException(status_code=422, detail="cannot report your own message")
        with conn.transaction():
            existing = conn.execute(
                "SELECT id, status FROM reports WHERE reporter_id = %s "
                "AND conversation_id = %s AND seq = %s AND status = 'open'",
                (user.id, body.conversation_id, body.seq),
            ).fetchone()
            if existing is not None:  # repeat report of the same message: same answer
                return ReportOut(id=existing[0], status=existing[1])
            report_id = conn.execute(
                "INSERT INTO reports (tenant_id, reporter_id, conversation_id, seq, reason) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (user.tenant_id, user.id, body.conversation_id, body.seq, body.reason),
            ).fetchone()[0]
            audit(
                conn,
                user.tenant_id,
                user.id,
                "report.create",
                {
                    "report_id": str(report_id),
                    "conversation_id": str(body.conversation_id),
                    "seq": body.seq,
                },
            )
    return ReportOut(id=report_id, status="open")
