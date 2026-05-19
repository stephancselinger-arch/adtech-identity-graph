from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.models.identity import IdentityId, IdType, ConsentSignals
from app.services import graph


def delete_by_uid(uid: str) -> tuple[str, int]:
    return graph.delete_identity(uid)


def delete_by_id(id_type: str, id_value: str) -> tuple[Optional[str], int]:
    try:
        id_ = IdentityId(type=IdType(id_type), value=id_value)
    except ValueError:
        return None, 0
    profile = graph.get_profile_by_id(id_)
    if not profile:
        return None, 0
    return graph.delete_identity(profile.uid)


def update_consent(uid: str, update: dict) -> Optional[object]:
    profile = graph.get_profile(uid)
    if not profile:
        return None
    existing = profile.consent or ConsentSignals()
    data = existing.model_dump()
    data.update({k: v for k, v in update.items() if v is not None})
    profile.consent = ConsentSignals(**data)
    profile.updated_at = datetime.now(timezone.utc)
    return profile
