from __future__ import annotations

import hashlib

from app.models.identity import IdType
from app.utils.hashing import hash_email, hash_phone, normalize_email, normalize_phone


def test_email_hash_case_insensitive():
    h1 = hash_email("User@Example.COM")
    h2 = hash_email("user@example.com")
    assert h1.value == h2.value


def test_email_hash_strips_whitespace():
    h1 = hash_email("  user@example.com  ")
    h2 = hash_email("user@example.com")
    assert h1.value == h2.value


def test_email_hash_is_sha256():
    h = hash_email("test@example.com")
    expected = hashlib.sha256("test@example.com".encode()).hexdigest()
    assert h.value == expected
    assert h.type == IdType.EMAIL_HASH


def test_phone_hash_normalizes_formatting():
    h1 = hash_phone("(212) 555-1234")
    h2 = hash_phone("2125551234")
    h3 = hash_phone("+1-212-555-1234")
    assert h1.value == h2.value == h3.value


def test_phone_hash_type():
    h = hash_phone("2125551234")
    assert h.type == IdType.PHONE_HASH


def test_normalize_email():
    assert normalize_email("  TEST@EXAMPLE.COM  ") == "test@example.com"


def test_normalize_phone_adds_us_prefix():
    assert normalize_phone("2125551234") == "12125551234"


def test_normalize_phone_keeps_existing_country_code():
    assert normalize_phone("+12125551234") == "12125551234"
