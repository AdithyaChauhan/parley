import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings

ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 7
JWT_ALGORITHM = "HS256"

_password_hasher = PasswordHasher()


def normalize_email(email: str) -> str:
    """Trim spaces and lowercase, so " Ana@Mail.com" and "ana@mail.com" match."""
    return email.strip().lower()


# --- Passwords (argon2) ---


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


# --- Access token (JWT, 15 minutes) ---


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # "subject": who this token is for
        "sid": str(session_id),  # which logged-in device it came from
        "iat": now,  # "issued at"
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),  # "expires"
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Return the token's contents. Raises jwt.InvalidTokenError if the token
    is fake, was changed, or has expired."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "sid", "exp"]},
    )


# --- Refresh token (random, 7 days) ---


def new_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """The SHA-256 fingerprint we store in the sessions table."""
    return hashlib.sha256(token.encode()).hexdigest()
