from __future__ import annotations

import hashlib
from typing import Optional

from app.models.identity import IdentityId, IdType

# Fingerprinting requires at least IP + UA to be meaningful
_MIN_COMPONENTS = 2


def compute_fingerprint(
    ip: Optional[str],
    user_agent: Optional[str],
    accept_language: Optional[str] = None,
) -> Optional[IdentityId]:
    parts = [p.strip() for p in [ip, user_agent, accept_language] if p and p.strip()]
    if len(parts) < _MIN_COMPONENTS:
        return None
    raw = "|".join(parts).lower()
    fp = hashlib.sha256(raw.encode()).hexdigest()
    return IdentityId(type=IdType.FINGERPRINT, value=fp)
