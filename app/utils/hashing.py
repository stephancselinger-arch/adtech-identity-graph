from __future__ import annotations

import hashlib
import re

from app.models.identity import IdentityId, IdType


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    # Assume 10-digit US number → prepend country code 1
    if len(digits) == 10:
        digits = "1" + digits
    return digits


def hash_email(email: str) -> IdentityId:
    normalized = normalize_email(email)
    hashed = hashlib.sha256(normalized.encode()).hexdigest()
    return IdentityId(type=IdType.EMAIL_HASH, value=hashed)


def hash_phone(phone: str) -> IdentityId:
    normalized = normalize_phone(phone)
    hashed = hashlib.sha256(normalized.encode()).hexdigest()
    return IdentityId(type=IdType.PHONE_HASH, value=hashed)
