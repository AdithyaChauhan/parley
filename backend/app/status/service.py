"""Who sees whose statuses (D41): the people I have a direct chat with. There's
no contacts list, so a direct chat is the closest thing to "people I know"."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.auth.models import User
from app.chats.models import Chat, ChatMember
from app.chats.service import direct_key
from app.status.models import Status

# How long a status lasts once it's posted.
LIFETIME = timedelta(hours=24)


def now() -> datetime:
    return datetime.now(UTC)


def status_key(user_id: uuid.UUID, status_id: uuid.UUID) -> str:
    """A photo's place in the store, made of ids only, like file_key (D38)."""
    return f"status/{user_id}/{status_id}"


def audience(db: Session, user_id: uuid.UUID) -> dict[uuid.UUID, str]:
    """Everyone I have a direct chat with, and their names. It works both ways:
    they see mine and I see theirs."""
    me, other = aliased(ChatMember), aliased(ChatMember)
    rows = db.execute(
        select(other.user_id, User.name)
        .select_from(me)
        .join(Chat, (Chat.id == me.chat_id) & (Chat.kind == "direct"))
        .join(other, (other.chat_id == me.chat_id) & (other.user_id != me.user_id))
        .join(User, User.id == other.user_id)
        .where(me.user_id == user_id)
    )
    return {row.user_id: row.name for row in rows}


def is_live(status: Status | None) -> bool:
    """Posted, and its 24 hours aren't up."""
    return status is not None and status.posted_at is not None and status.expires_at > now()


def can_see(db: Session, viewer_id: uuid.UUID, status: Status | None) -> bool:
    """The poster, or someone they have a direct chat with, while it's live."""
    if not is_live(status):
        return False
    if status.user_id == viewer_id:
        return True
    key = direct_key(viewer_id, status.user_id)
    return db.scalar(select(Chat.id).where(Chat.direct_key == key)) is not None


def quote_for_reply(db: Session, chat_id: uuid.UUID, me_id: uuid.UUID, status_id: uuid.UUID) -> dict | None:
    """A reply to a status goes into our direct chat with a small copy of the
    status, so it still makes sense after the status is gone. None if the status
    can't be quoted here (gone, mine, or not this chat's person): the reply is
    then sent as a plain message, never refused."""
    status = db.get(Status, status_id)
    chat = db.get(Chat, chat_id)
    if not is_live(status) or chat is None or status.user_id == me_id:
        return None
    if chat.direct_key != direct_key(me_id, status.user_id):
        return None
    data = status.data or {}
    return {
        "status": {
            "id": str(status.id),
            "kind": status.kind,
            # The start only: enough to remember which status it was.
            "body": status.body[:100],
            "color": status.color,
            "preview": data.get("preview"),
        }
    }
