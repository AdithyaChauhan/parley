import uuid
from typing import Literal, NamedTuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.auth.models import User
from app.chats.models import Chat, ChatMember
from app.chats.schemas import ChatOut, LastMessageOut
from app.live import bus
from app.messages.models import EVENT_KINDS, REAL_KINDS, Message
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


def member_ids(db: Session, chat_id: uuid.UUID, seq: int | None = None) -> list[uuid.UUID]:
    """Who a chat's live events go to (D37).
    No seq: the current members (receipts, typing).
    With seq: everyone who can see message #seq, so the "removed" note still
    reaches the person removed, and a new member never gets older messages."""
    query = select(ChatMember.user_id).where(ChatMember.chat_id == chat_id)
    if seq is None:
        query = query.where(ChatMember.until_seq.is_(None))
    else:
        query = query.where(
            ChatMember.from_seq <= seq,
            or_(ChatMember.until_seq.is_(None), ChatMember.until_seq >= seq),
        )
    return list(db.scalars(query))


def partner_ids(db: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Everyone who has a direct chat with this person: the people who see
    their online status, so they get their "online" news (D22). Groups show
    member names, not online (D37), so a 50-person group adds no presence pushes."""
    my_chats = (
        select(ChatMember.chat_id)
        .join(Chat, Chat.id == ChatMember.chat_id)
        .where(ChatMember.user_id == user_id, Chat.kind == "direct")
    )
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


def _capped(db: Session, chat_id: uuid.UUID, user_id: uuid.UUID, seq: int) -> int | None:
    """seq, but never past the last message this person can see: nobody can
    have #99 in a chat that ends at #12, and someone who left at #12 can't
    have #13 (D37). None if they aren't in the chat, or there's no such chat."""
    row = db.execute(
        select(Chat.last_seq, ChatMember.until_seq)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(Chat.id == chat_id, ChatMember.user_id == user_id)
    ).one_or_none()
    if row is None:
        return None
    end = row.last_seq if row.until_seq is None else row.until_seq
    return min(seq, end)


def mark_delivered(db: Session, chat_id: uuid.UUID, user_id: uuid.UUID, seq: int) -> Bookmarks | None:
    """Move this person's "delivered up to" bookmark forward to seq (D20).
    Returns both bookmarks after the move, or None if nothing moved: not a
    member, no such chat, or seq isn't ahead of the bookmark."""
    target = _capped(db, chat_id, user_id, seq)
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
    target = _capped(db, chat_id, user_id, seq)
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


def group_low(db: Session, chat_id: uuid.UUID) -> Bookmarks | None:
    """A group's lowest "delivered" and "read" over its current members: the
    only thing a group's ticks show (D37). None for a direct chat."""
    row = db.execute(
        select(func.min(ChatMember.delivered_up_to), func.min(ChatMember.read_up_to))
        .join(Chat, Chat.id == ChatMember.chat_id)
        .where(ChatMember.chat_id == chat_id, ChatMember.until_seq.is_(None), Chat.kind == "group")
    ).one()
    return None if row[0] is None else Bookmarks(row[0], row[1])


def group_receipt(chat_id: uuid.UUID, low: Bookmarks) -> dict:
    """The group's ticks moved: "everyone has it up to #d, has read up to #r" (D37)."""
    return {
        "type": "group_receipt",
        "data": {"chat_id": str(chat_id), "delivered_up_to": low.delivered_up_to, "read_up_to": low.read_up_to},
    }


def low_moved(db: Session, chat_id: uuid.UUID, before: Bookmarks) -> tuple[list[uuid.UUID], dict] | None:
    """In a group, after one member's bookmarks moved up from `before` (and
    were committed): if that lifted the group's lowest, the group receipt and
    its current members. Otherwise None, and nothing is pushed.
    The lowest is read after the commit, so when two members move at once,
    the later one always sees both moves, and a lift is never missed. Both
    may push the same numbers, which is harmless: the app keeps the higher."""
    low = group_low(db, chat_id)
    if low is None:
        return None
    if before.delivered_up_to >= low.delivered_up_to and before.read_up_to >= low.read_up_to:
        return None  # I wasn't the one holding it back
    return member_ids(db, chat_id), group_receipt(chat_id, low)


def save_bookmark(
    db: Session, chat_id: uuid.UUID, user_id: uuid.UUID, kind: Literal["delivered", "read"], seq: int
) -> Bookmarks | None:
    """Move this person's "delivered" or "read" bookmark to seq and, if it
    moved, push the news (D20, D37):
    - direct chat: a receipt to both people, their own tabs too;
    - group: a receipt to their own tabs only (for unread), and a group
      receipt to every current member only if the group's lowest moved.
    The one function behind both doors: the live line and the HTTP routes.
    Returns both bookmarks, or None if nothing moved (not a member, no such
    chat, or not a step forward). Then nothing is pushed."""
    before = db.execute(
        select(Chat.kind, ChatMember.delivered_up_to, ChatMember.read_up_to)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(Chat.id == chat_id, ChatMember.user_id == user_id)
    ).one_or_none()
    if before is None:
        return None  # not a member, or no such chat

    mark = mark_read if kind == "read" else mark_delivered
    # Saved first (mark_* commits), pushed after: a receipt never announces a
    # bookmark that isn't in PostgreSQL yet.
    moved = mark(db, chat_id, user_id, seq)
    if moved is None:
        return None

    # Both bookmarks, so the app can pick grey or teal ticks (D20).
    receipt = {
        "type": "receipt",
        "data": {
            "chat_id": str(chat_id),
            "user_id": str(user_id),
            "delivered_up_to": moved.delivered_up_to,
            "read_up_to": moved.read_up_to,
        },
    }
    if before.kind == "group":
        # Sending everyone's every move to all 50 swamped the copies (T35's
        # load test): my own tabs need it, the others only need the lowest.
        to = [user_id]
        lifted = low_moved(db, chat_id, Bookmarks(before.delivered_up_to, before.read_up_to))
    else:
        # It moved, so they're in the chat: no stranger gets the receipt.
        to = list({*member_ids(db, chat_id), user_id})
        lifted = None
    # The connection goes back before the push, so a slow Redis can't hold it (D34).
    db.close()
    # Never raises: with Redis down the bookmark is still saved, and the ticks
    # catch up later (D24).
    bus.publish(to, receipt)
    if lifted is not None:
        bus.publish(*lifted)
    return moved


def _last_message(message: Message | None, sender_name: str | None) -> LastMessageOut | None:
    if message is None:
        return None
    return LastMessageOut(
        seq=message.seq,
        # A group note has no text: the app writes its words from data (D37).
        preview=message.body[:PREVIEW_LENGTH],
        created_at=message.created_at,
        kind=message.kind,
        sender_id=message.sender_id,
        sender_name=sender_name,
        # The chat list only needs a file's name and category, not its picture.
        data={k: v for k, v in message.data.items() if k != "preview"} if message.data else None,
        deleted=message.deleted_at is not None,
    )


def list_my_chats(db: Session, me: User, chat_id: uuid.UUID | None = None) -> list[ChatOut]:
    """My chat list, newest activity first. Pass chat_id to get just that one row.
    Chats I left or was removed from stay in it, read-only (D37)."""
    other_member = aliased(ChatMember)
    sender = aliased(User)
    # The last number I can see: the chat's last, or the note that ended my
    # membership (D37).
    my_last_seq = func.coalesce(ChatMember.until_seq, Chat.last_seq)
    # The preview skips reactions, edits and deletes (D39): the last row at or
    # below that number that's a message or a group note.
    row = aliased(Message)
    last_shown_seq = (
        select(row.seq)
        .where(row.chat_id == Chat.id, row.seq <= my_last_seq, row.kind.not_in(EVENT_KINDS))
        .order_by(row.seq.desc())
        .limit(1)
        .correlate(Chat, ChatMember)
        .scalar_subquery()
    )
    # Unread counts only real messages: not events, not group notes (D39).
    unread_row = aliased(Message)
    unread_count = (
        select(func.count())
        .select_from(unread_row)
        .where(
            unread_row.chat_id == Chat.id,
            unread_row.seq > ChatMember.read_up_to,
            unread_row.seq <= my_last_seq,
            unread_row.kind.in_(REAL_KINDS),
        )
        .correlate(Chat, ChatMember)
        .scalar_subquery()
    )
    query = (
        select(Chat, ChatMember, User.id, User.name, Message, sender.name, unread_count)
        .select_from(Chat)
        # Only chats I'm in (or was in), with my row.
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
        # The last message I can see. None if the chat is empty.
        .outerjoin(Message, and_(Message.chat_id == Chat.id, Message.seq == last_shown_seq))
        # Its sender, for "Ana: hi" in a group's row.
        .outerjoin(sender, sender.id == Message.sender_id)
        # Newest message first. A chat with no messages counts from when it was made.
        .order_by(func.coalesce(Message.created_at, Chat.created_at).desc())
    )
    if chat_id is not None:
        query = query.where(Chat.id == chat_id)

    rows = list(db.execute(query))
    # The connection goes back before Redis, so a slow Redis can't hold it (D34).
    # The rows keep their values.
    db.close()
    # Everyone's online status in one trip to Redis, not one per row (D24).
    # From Redis, not the database: a fast, temporary fact (D22).
    found = presence.statuses([other_id for _, _, other_id, *_ in rows if other_id is not None])

    chats = []
    for chat, mine, other_id, other_name, last, sender_name, unread in rows:
        # Groups have no other person, so nobody to be online.
        status = found.get(other_id, presence.UNKNOWN)
        is_group = chat.kind == "group"
        chats.append(
            ChatOut(
                id=chat.id,
                kind=chat.kind,
                # Groups have no "other person", so they show their name.
                name=other_name or chat.title,
                last_message=_last_message(last, sender_name),
                unread=unread,
                other_user_id=other_id,
                online=status.online,
                last_seen=status.last_seen,
                role=mine.role if is_group else None,
                left=not mine.current,
            )
        )
    return chats
