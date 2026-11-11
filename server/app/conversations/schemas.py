from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ConversationCreate(BaseModel):
    kind: Literal["private", "public", "announcement"]
    title: str | None = Field(default=None, max_length=120)
    community_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ConversationOut(BaseModel):
    id: UUID
    tenant_id: UUID
    kind: str
    title: str | None
    created_by: UUID
    created_at: datetime