import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.messages.models import Message

# Spaces at both ends are trimmed first, so "   " counts as empty and is refused.
MessageText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


# --- What comes in ---


class SendMessageRequest(BaseModel):
    # Made by the sender's app once per message, and sent again on a retry (D9).
    client_msg_id: uuid.UUID
    body: MessageText


class EditMessageRequest(BaseModel):
    body: MessageText


class ReactionRequest(BaseModel):
    # The only six allowed (D39). The app's list must match these exactly.
    emoji: Literal["👍", "❤️", "😂", "😮", "😢", "🙏"]


# --- What goes out ---


class MessageOut(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    seq: int
    sender_id: uuid.UUID
    # Shown above the bubble in a group (D37). Sent with each message, so a
    # message from someone who has since left still has a name.
    sender_name: str
    client_msg_id: uuid.UUID
    body: str
    created_at: datetime
    # "text", "system" for a group note, whose words the app writes from data
    # (D37), or "file", with the file's details in data (D38).
    # "reaction", "edit" or "delete": a change to another message, not one to
    # show (D39). data has target_seq, and target is that message as it is now.
    kind: str
    data: dict | None
    edited: bool
    deleted: bool
    # Emoji → the people who picked it (D39).
    reactions: dict[str, list[uuid.UUID]]
    # The number of the last change to this message: the higher copy wins.
    state_seq: int
    # Events only. Null if this person can't see the message it points at (D37).
    target: "MessageOut | None" = None

    @classmethod
    def of(
        cls,
        message: Message,
        sender_name: str,
        reactions: dict[str, list[uuid.UUID]] | None = None,
        target: "MessageOut | None" = None,
    ) -> "MessageOut":
        return cls(
            id=message.id,
            chat_id=message.chat_id,
            seq=message.seq,
            sender_id=message.sender_id,
            sender_name=sender_name,
            client_msg_id=message.client_msg_id,
            body=message.body,
            created_at=message.created_at,
            kind=message.kind,
            data=message.data,
            edited=message.edited_at is not None,
            deleted=message.deleted_at is not None,
            reactions=reactions or {},
            state_seq=message.state_seq,
            target=target,
        )


class MemberOut(BaseModel):
    """One person in the chat with their two tick bookmarks (D9)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    delivered_up_to: int
    read_up_to: int


class MessagePage(BaseModel):
    """Up to `limit` messages: newest first, or oldest first with after= (D21)."""

    messages: list[MessageOut]
    # Every number from low_seq to high_seq is settled by this page: it's in
    # messages, or it's an event whose result those messages already show (D39).
    # Without these, the numbers history leaves out would look like holes.
    # Null when the page settles nothing.
    low_seq: int | None
    high_seq: int | None
    # True if there are more past these. Normally older ones: ask again with
    # before=<smallest seq>. With after=, newer ones: ask again with after=<biggest seq>.
    has_more: bool
    # Everyone's bookmarks, so the app can draw the right ticks after a reload too.
    # In a group, only the current members: ticks wait for them alone (D37).
    members: list[MemberOut]
