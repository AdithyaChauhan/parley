import uuid
from typing import NamedTuple

from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.auth.models import User
from app.chats.models import Chat, ChatMember
from app.chats.schemas import ChatOut, LastMessageOut
from app.messages.models import Message
from app.presence import service as presence

# How many letters of the last message the chat list shows.
PREVIEW_LENGTH = 100


def direct_key(a: uuid.UUID, b: uuid.UUID) -> str:
    """The same label for the same two people, whoever starts the chat."""
    return ":".join(sorted([str(a), str(b)]))


def _find_direct_chat(db: Session, key: str) -> Chat | None:
    return db.scalar(select(Chat).where(Chat.direct_key == key))


def get_or_create_direct_chat(db: Session, me: User, other: User) -> tuple[Chat, bool]:
    """Returns (chat, created). If the two already have a direct chat,
    returns that one instead of making a second (D18)."""
    key = direct_key(me.id, other.id)
    existing = _find_direct_chat(db, key)
    if existing is not None:
        return existing, False

    chat = Chat(kind="direct", direct_key=key)
    db.add(chat)
    try:
        db.flush()  # sends the chat row now, so it gets its id for the members
        db.add_all([
            ChatMember(chat_id=chat.id, user_id=me.id),
            ChatMember(chat_id=chat.id, user_id=other.id),
        ])
        # The chat and both members are saved together, or not at all.
        db.commit()
    except IntegrityError:
        # The other person started the same chat at the same moment, and theirs
        # was saved first: the UNIQUE direct_key refused ours. Use theirs.
        db.rollback()
        existing = _find_direct_chat(db, key)
        if existing is None:
            raise  # refused for some other reason: don't hide it
        return existing, False

    return chat, True


def get_member(db: Session, chat_id: uuid.UUID, user_id: uuid.UUID) -> ChatMember | None:
    """This person's row in this chat. None if they aren't in it, or there's no such chat."""
    return db.get(ChatMember, (chat_id, user_id))


def member_ids(db: Session, chat_id: uuid.UUID) -> list[uuid.UUID]:
    """Everyone in this chat: the people its live events go to."""
    return list(db.scalars(select(ChatMember.user_id).where(ChatMember.chat_id == chat_id)))


def partner_ids(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Everyone who shares at least one chat with this person: the people who
    see them in their chat list, so they get their "online" news (D22)."""
    my_chats = select(ChatMember.chat_id).where(ChatMember.user_id == user_id)
    return list(
        db.scalars(
            select(ChatMember.user_id)
            .where(ChatMember.chat_id.in_(my_chats), ChatMember.user_id != user_id)
            .distinct()  # once each, even if we share several chats
        )
    )


class Bookmarks(NamedTuple):
    """One person's two tick bookmarks in a chat, right after a move (D9)."""

    delivered_up_to: int
    read_up_to: int


def _capped(db: Session, chat_id: uuid.UUID, seq: int) -> int | None:
    """seq, but never past the chat's last message: nobody can have #99 in a
    chat that ends at #12. None if there's no such chat."""
    last_seq = db.scalar(select(Chat.last_seq).where(Chat.id == chat_id))
    if last_seq is None:
        return None
    return min(seq, last_seq)


def mark_delivered(db: Session, chat_id: uuid.UUID, user_id: uuid.UUID, seq: int) -> Bookmarks | None:
    """Move this person's "delivered up to" bookmark forward to seq (D20).
    Returns both bookmarks after the move, or None if nothing moved: not a
    member, no such chat, or seq isn't ahead of the bookmark."""
    target = _capped(db, chat_id, seq)
    if target is None:
        return None

    # Only matches if the person is in the chat AND it's a step forward. The
    # row is locked while it changes, so two tabs reporting at once can't
    # move it backwards: the second one re-checks against the new value.
    row = db.execute(
        update(ChatMember)
        .where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
            ChatMember.delivered_up_to < target,
        )
        .values(delivered_up_to=target)
        .returning(ChatMember.delivered_up_to, ChatMember.read_up_to)
    ).one_or_none()
    db.commit()
    return None if row is None else Bookmarks(row.delivered_up_to, row.read_up_to)


def mark_read(db: Session, chat_id: uuid.UUID, user_id: uuid.UUID, seq: int) -> Bookmarks | None:
    """Move this person's "read up to" bookmark forward to seq (D20). Read
    implies delivered, so "delivered up to" is lifted to at least seq too.
    Returns both bookmarks after the move, or None if nothing moved (the
    same reasons as mark_delivered)."""
    target = _capped(db, chat_id, seq)
    if target is None:
        return None

    # The same forward-only UPDATE as mark_delivered, on read_up_to.
    # GREATEST keeps the bigger of the two: reading #3 after #5 was
    # delivered must not pull "delivered" back to 3.
    row = db.execute(
        update(ChatMember)
        .where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
            ChatMember.read_up_to < target,
        )
        .values(read_up_to=target, delivered_up_to=func.greatest(ChatMember.delivered_up_to, target))
        .returning(ChatMember.delivered_up_to, ChatMember.read_up_to)
    ).one_or_none()
    db.commit()
    return None if row is None else Bookmarks(row.delivered_up_to, row.read_up_to)


def list_my_chats(db: Session, me: User, chat_id: uuid.UUID | None = None) -> list[ChatOut]:
    """My chat list, newest activity first. Pass chat_id to get just that one row."""
    other_member = aliased(ChatMember)
    query = (
        select(Chat, ChatMember.read_up_to, User.id, User.name, Message)
        .select_from(Chat)
        # Only chats I'm in, with my bookmark.
        .join(ChatMember, and_(ChatMember.chat_id == Chat.id, ChatMember.user_id == me.id))
        # Direct chats: the other person's row, then their id and name.
        .outerjoin(
            other_member,
            and_(
                other_member.chat_id == Chat.id,
                other_member.user_id != me.id,
                Chat.kind == "direct",
            ),
        )
        .outerjoin(User, User.id == other_member.user_id)
        # The last message is the one numbered last_seq. None if the chat is empty.
        .outerjoin(Message, and_(Message.chat_id == Chat.id, Message.seq == Chat.last_seq))
        # Newest message first. A chat with no messages counts from when it was made.
        .order_by(func.coalesce(Message.created_at, Chat.created_at).desc())
    )
    if chat_id is not None:
        query = query.where(Chat.id == chat_id)

    rows = list(db.execute(query))
    # Everyone's online status in one trip to Redis, not one per row (D24).
    # From Redis, not the database: a fast, temporary fact (D22).
    found = presence.statuses([other_id for _, _, other_id, _, _ in rows if other_id is not None])

    chats = []
    for chat, read_up_to, other_id, other_name, last in rows:
        last_message = None
        if last is not None:
            last_message = LastMessageOut(
                seq=last.seq, preview=last.body[:PREVIEW_LENGTH], created_at=last.created_at
            )
        # Groups (v2) have no other person, so nobody to be online.
        status = found.get(other_id, presence.UNKNOWN)
        chats.append(
            ChatOut(
                id=chat.id,
                kind=chat.kind,
                # Groups (v2) have no "other person", so they show their title.
                name=other_name or chat.title,
                last_message=last_message,
                unread=chat.last_seq - read_up_to,
                other_user_id=other_id,
                online=status.online,
                last_seen=status.last_seen,
            )
        )
    return chats
