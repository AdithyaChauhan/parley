import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PushSubscription(Base):
    """One browser that said yes to notifications, for the user logged in on
    it (D26). Ben with Edge and Firefox has two rows."""

    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Indexed: the worker looks up "all of Ben's devices" for every job.
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # The browser's address at its push service (Google's, Mozilla's...).
    # Unique: one browser is one row, owned by whoever subscribed on it last.
    endpoint: Mapped[str] = mapped_column(unique=True)
    # The browser's two keys. Pushes are locked with them, so only that
    # browser can open them, not the push service in between.
    p256dh: Mapped[str]
    auth: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
