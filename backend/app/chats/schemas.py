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
    # The other person in a direct chat (null for groups), so the app can match
    # their live "presence" news to this row.
    other_user_id: uuid.UUID | None
    # Direct chats: is the other person online now, and when their app was
    # last seen (D22). False and null for groups (v2); null if never seen.
    online: bool
    last_seen: datetime | None
