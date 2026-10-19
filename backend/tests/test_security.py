import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.auth.security import (
    JWT_ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    normalize_email,
    verify_password,
)
from app.config import settings


def test_password_hash_checks_right_and_wrong_password():
    password_hash = hash_password("secret123")

    assert password_hash != "secret123"
    assert verify_password("secret123", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_same_password_gives_different_hashes():
    # Each hash gets its own random salt.
    assert hash_password("secret123") != hash_password("secret123")


def test_access_token_round_trip():
    user_id, session_id = uuid.uuid4(), uuid.uuid4()

    payload = decode_access_token(create_access_token(user_id, session_id))

    assert payload["sub"] == str(user_id)
    assert payload["sid"] == str(session_id)


def test_expired_access_token_is_rejected():
    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "sid": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)


def test_token_signed_with_another_secret_is_rejected():
    forged = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "sid": str(uuid.uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
        "not-the-real-secret-" * 3,
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)


def test_refresh_token_fingerprint_is_stable_and_not_the_token():
    token = new_refresh_token()

    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token


def test_email_is_trimmed_and_lowercased():
    assert normalize_email("  Ana.Silva@Example.COM ") == "ana.silva@example.com"
