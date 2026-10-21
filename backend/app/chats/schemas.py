import uuid
from datetime import datetime

from pydantic import BaseModel

from app.auth.schemas import Email


# --- What comes in ---


class StartDirectChatRequest(BaseModel):
    # Trimmed and lowercased, the same as at sign-up, so it matches the saved email.
    email: Email


# --- What goes out ---


class LastMessageOut(BaseModel):
    seq: int
    # Only the start of the text: the grey line under the chat's name.
    preview: str
    created_at: datetime


class ChatOut(BaseModel):
    """One row of the chat list."""

    id: uuid.UUID
    kind: str
    # The other person's name for direct chats.
    name: str
    # Empty (null) for a chat with no messages yet.
    last_message: LastMessageOut | None
    unread: int
