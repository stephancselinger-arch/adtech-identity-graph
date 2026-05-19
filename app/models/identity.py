from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class IdType(str, Enum):
    COOKIE = "cookie"
    DEVICE = "device"           # IDFA / GAID
    EMAIL_HASH = "email_hash"   # SHA-256 of normalized email
    PHONE_HASH = "phone_hash"   # SHA-256 of normalized E.164 phone
    PPID = "ppid"               # Publisher-Provided ID
    UID2 = "uid2"               # Unified ID 2.0 token
    FINGERPRINT = "fingerprint" # probabilistic IP+UA hash


class IdentityId(BaseModel):
    type: IdType
    value: str


class ConsentSignals(BaseModel):
    gdpr: Optional[int] = None          # 1 = GDPR applies
    gdpr_consent: Optional[str] = None  # TC string
    us_privacy: Optional[str] = None    # CCPA string


class IdentityProfile(BaseModel):
    uid: str = Field(default_factory=lambda: f"uid_{uuid.uuid4().hex}")
    ids: list[IdentityId] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    consent: Optional[ConsentSignals] = None
    suppressed: bool = False
    match_confidence: float = 1.0  # 1.0=deterministic, <1.0=probabilistic


class IdentityEvent(BaseModel):
    """IDs observed together in a single user interaction — triggers merging."""
    ids: list[IdentityId]
    source: Optional[str] = None
    timestamp: Optional[datetime] = None
    consent: Optional[ConsentSignals] = None


class ResolveRequest(BaseModel):
    ids: list[IdentityId]
    consent: Optional[ConsentSignals] = None
    create_if_missing: bool = True


class ResolveResponse(BaseModel):
    uid: str
    ids: list[IdentityId]
    merged: bool = False
    created: bool = False
    match_confidence: float = 1.0
    suppressed: bool = False


class MergeRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    survivor_uid: str
    absorbed_uid: str
    trigger_ids: list[IdentityId] = Field(default_factory=list)
    merged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
