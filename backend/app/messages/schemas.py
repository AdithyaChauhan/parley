import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


# --- What comes in ---


class SendMessageRequest(BaseModel):
    # Made by the sender's app once per message, and sent again on a retry (D9).
    client_msg_id: uuid.UUID
    # Spaces at both ends are trimmed first, so "   " counts as empty and is refused.
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


# --- What goes out ---


class MessageOut(BaseModel):
    # from_attributes: lets pydantic read straight from a Message row.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chat_id: uuid.UUID
    seq: int
    sender_id: uuid.UUID
    client_msg_id: uuid.UUID
    body: str
    created_at: datetime


class MessagePage(BaseModel):
    """Up to `limit` messages, newest first."""

    messages: list[MessageOut]
    # True if there are older messages above these: ask again with before=<smallest seq>.
    has_more: bool
