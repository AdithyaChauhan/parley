import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Chat(Base):
    """One conversation: a direct chat between two people, or a group."""

    __tablename__ = "chats"
    # The database refuses any kind except these two.
    __table_args__ = (
        CheckConstraint("kind IN ('direct', 'group')", name="chats_kind_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    kind: Mapped[str]
    # Empty for direct chats: the app shows the other person's name instead.
    title: Mapped[str] = mapped_column(server_default="")
    # Direct chats only: the two user ids, sorted and joined. UNIQUE, so the
    # same two people can't end up with two direct chats (D18).
    # Empty (NULL) for groups; empty cells never clash with a UNIQUE rule.
    direct_key: Mapped[str | None] = mapped_column(unique=True)
    # The counter: the last message number handed out in this chat (D18).
    last_seq: Mapped[int] = mapped_column(server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChatMember(Base):
    """One person in one chat, with their two tick bookmarks (D9)."""

    __tablename__ = "chat_members"

    # The key is the pair: one row per person per chat.
    chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True
    )
    # Its own index too, for "list my chats" (find all rows for one user).
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Bookmarks: every message up to this number reached this person's app
    # (two grey ticks) / was read by them (two blue ticks).
    delivered_up_to: Mapped[int] = mapped_column(server_default="0")
    read_up_to: Mapped[int] = mapped_column(server_default="0")
