from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class DeletionRequest(BaseModel):
    uid: Optional[str] = None
    id_type: Optional[str] = None
    id_value: Optional[str] = None
    reason: str = "user_request"


class DeletionResult(BaseModel):
    uid: str
    ids_deleted: int
    success: bool
    deleted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsentUpdate(BaseModel):
    uid: str
    gdpr: Optional[int] = None
    gdpr_consent: Optional[str] = None
    us_privacy: Optional[str] = None


class SuppressCheck(BaseModel):
    id_type: str
    id_value: str
    suppressed: bool
