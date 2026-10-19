import uuid
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, StringConstraints

from app.auth.security import normalize_email


def _clean_email(value):
    return normalize_email(value) if isinstance(value, str) else value


# Trim and lowercase first, then check it looks like a real email address.
Email = Annotated[EmailStr, BeforeValidator(_clean_email)]


# --- What comes in ---


class SignupRequest(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=50)]
    email: Email
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: Email
    # No length rule here: log-in only checks if the password matches.
    password: str


# --- What goes out ---


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    # from_attributes: lets pydantic read straight from a User row.
    # Only these three fields are sent, so password_hash never leaves the server.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
