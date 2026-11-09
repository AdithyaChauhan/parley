import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# What people send: these count as unread, and can be reacted to (D39).
REAL_KINDS = ("text", "file")
# Changes to a message. Each has its own number in the chat, but isn't a message
# on screen: history leaves them out, and only catch-up brings them (D39).
EVENT_KINDS = ("reaction", "edit", "delete")


class Message(Base):
    """One message in one chat, numbered #1, #2, #3 inside that chat (D9)."""

    __tablename__ = "messages"
    __table_args__ = (
        # No two #8s in one chat (D18). Also makes "this chat's messages, in order" fast.
        UniqueConstraint("chat_id", "seq", name="messages_chat_seq_unique"),
        # A retried send is never saved twice (D18).
        UniqueConstraint("sender_id", "client_msg_id", name="messages_sender_client_msg_unique"),
        CheckConstraint(
            "kind IN ('text', 'system', 'file', 'reaction', 'edit', 'delete')", name="messages_kind_valid"
        ),
        # The side panel's file list reads only these rows (T36).
        Index("messages_chat_file_seq", "chat_id", "seq", postgresql_where=text("kind = 'file'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    # The message's number inside its chat, taken from chats.last_seq.
    seq: Mapped[int]
    # No CASCADE: deleting a user must never quietly delete messages in other people's chats.
    # For a group note (kind "system"), the person who did it.
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    # Made by the sender's app, once per message, and sent again on a retry.
    client_msg_id: Mapped[uuid.UUID]
    # The server only stores and passes this along; it never reads it (D12).
    body: Mapped[str] = mapped_column(Text)
    # "text": a normal message. "system": a group note (created, added, removed,
    # left, renamed, made admin), numbered like any message (D37). Its body is
    # empty, and data says who did what to whom; the app writes the words.
    # "file": a file or voice note (D38). Empty body, and data has its details.
    # "reaction", "edit", "delete": a change to another message (D39). Empty
    # body, so a deleted message's text can't live on here. data has target_seq.
    kind: Mapped[str] = mapped_column(server_default="text")
    data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Deleted for everyone: the body and data are erased, and the row stays so
    # the chat can show "This message was deleted" (D39).
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The number of the last change to this message, 0 if none. Pushes can
    # arrive out of order, so the app keeps whichever copy has the higher one.
    state_seq: Mapped[int] = mapped_column(server_default="0")


class Reaction(Base):
    """One person's reaction to one message. The key is the pair, so the
    database itself refuses a second one (D39)."""

    __tablename__ = "message_reactions"

    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    emoji: Mapped[str]
