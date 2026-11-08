import uuid
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.auth.schemas import Email

# The most people in a group, the creator included (D37).
MAX_MEMBERS = 50

# Trimmed first, so "   " counts as empty and is refused (D37: 1-50 characters).
GroupName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


# --- What comes in ---


class PeopleIn(BaseModel):
    """People to add (D37): picked from my direct chats (their user ids), or
    typed by exact email, like start-chat. There's no search or directory."""

    user_ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_MEMBERS)
    emails: list[Email] = Field(default_factory=list, max_length=MAX_MEMBERS)


class CreateGroupRequest(PeopleIn):
    name: GroupName


class RenameGroupRequest(BaseModel):
    name: GroupName


# --- What goes out ---


class GroupMemberOut(BaseModel):
    """One current member, for the side panel (D37)."""

    user_id: uuid.UUID
    name: str
    role: str  # "admin" or "member"
