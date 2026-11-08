import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Upload(Base):
    """A file someone got permission to upload (D38). message_id stays empty
    until its message is saved. An empty one after a day was never sent, so it's
    removed (cleanup.py)."""

    __tablename__ = "uploads"
    __table_args__ = (
        # Only the rows the daily cleanup looks at, so the index stays tiny.
        Index("uploads_unsent_created", "created_at", postgresql_where=text("message_id IS NULL")),
    )

    # Also the last part of the file's key in the store.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    # No CASCADE, like messages: deleting a user never quietly removes other people's files.
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(Text, unique=True)
    # What the sender's app said. The name is only ever shown, never used as a path.
    name: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str]
    size: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
