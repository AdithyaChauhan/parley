import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.auth.models import User
from app.chats.models import Chat, ChatMember
from app.chats.schemas import ChatOut, LastMessageOut
from app.messages.models import Message

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


def list_my_chats(db: Session, me: User, chat_id: uuid.UUID | None = None) -> list[ChatOut]:
    """My chat list, newest activity first. Pass chat_id to get just that one row."""
    other_member = aliased(ChatMember)
    query = (
        select(Chat, ChatMember.read_up_to, User.name, Message)
        .select_from(Chat)
        # Only chats I'm in, with my bookmark.
        .join(ChatMember, and_(ChatMember.chat_id == Chat.id, ChatMember.user_id == me.id))
        # Direct chats: the other person's row, then their name.
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

    chats = []
    for chat, read_up_to, other_name, last in db.execute(query):
        last_message = None
        if last is not None:
            last_message = LastMessageOut(
                seq=last.seq, preview=last.body[:PREVIEW_LENGTH], created_at=last.created_at
            )
        chats.append(
            ChatOut(
                id=chat.id,
                kind=chat.kind,
                # Groups (v2) have no "other person", so they show their title.
                name=other_name or chat.title,
                last_message=last_message,
                unread=chat.last_seq - read_up_to,
            )
        )
    return chats
