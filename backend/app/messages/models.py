import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Message(Base):
    """One message in one chat, numbered #1, #2, #3 inside that chat (D9)."""

    __tablename__ = "messages"
    __table_args__ = (
        # No two #8s in one chat (D18). Also makes "this chat's messages, in order" fast.
        UniqueConstraint("chat_id", "seq", name="messages_chat_seq_unique"),
        # A retried send is never saved twice (D18).
        UniqueConstraint("sender_id", "client_msg_id", name="messages_sender_client_msg_unique"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    # The message's number inside its chat, taken from chats.last_seq.
    seq: Mapped[int]
    # No CASCADE: deleting a user must never quietly delete messages in other people's chats.
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    # Made by the sender's app, once per message, and sent again on a retry.
    client_msg_id: Mapped[uuid.UUID]
    # The server only stores and passes this along; it never reads it (D12).
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
