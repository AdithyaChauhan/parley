import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Status(Base):
    """One status: a text or a photo that lasts 24 hours (D41). Seen by the
    people I have a direct chat with."""

    __tablename__ = "statuses"
    __table_args__ = (
        CheckConstraint("kind IN ('text', 'image')", name="statuses_kind_valid"),
        # "My people's statuses that haven't run out": the feed's only question.
        Index("statuses_user_expires", "user_id", "expires_at"),
    )

    # Made by the poster's app, like client_msg_id (D9): a retried post is never
    # saved twice. For a photo, also the last part of its key in the store.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str]
    # The words of a text status, or a photo's caption. Shown to my people only.
    body: Mapped[str] = mapped_column(Text, server_default="")
    # A text status's background: one of the app's 6 colors (0-5).
    color: Mapped[int] = mapped_column(server_default="0")
    # Photos: the store key, type, size, and the browser's measurements and tiny preview.
    data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Empty while the photo is still uploading. Nobody sees it until then (D9).
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # posted_at + 24 h. Reads stop at this time; the hourly job removes the row later.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StatusView(Base):
    """Someone saw one of my statuses. The pair is the key, so seeing it twice
    counts once."""

    __tablename__ = "status_views"
    __table_args__ = (
        # Rows go when their status goes (CASCADE), so this stays small.
        Index("status_views_status", "status_id", text("viewed_at DESC")),
    )

    status_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("statuses.id", ondelete="CASCADE"), primary_key=True)
    viewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
