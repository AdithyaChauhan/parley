import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.chats.models import Chat, ChatMember
from app.messages.models import Message


class NotAMember(Exception):
    """The sender left or was removed: they can't send here any more (D37)."""


def _find_sent(db: Session, sender_id: uuid.UUID, client_msg_id: uuid.UUID) -> Message | None:
    return db.scalar(
        select(Message).where(
            Message.sender_id == sender_id, Message.client_msg_id == client_msg_id
        )
    )


def take_seq(db: Session, chat_id: uuid.UUID) -> int | None:
    """The chat's next number (D18). This UPDATE locks the chat's row until the
    commit, so another sender, or a member change, in the same chat waits here,
    then gets the number after ours. None if there's no such chat."""
    return db.scalar(
        update(Chat)
        .where(Chat.id == chat_id)
        .values(last_seq=Chat.last_seq + 1)
        .returning(Chat.last_seq)
    )


def mark_sent(db: Session, chat_id: uuid.UUID, sender_id: uuid.UUID, seq: int) -> None:
    """The sender has read their own message, so it never counts as unread for
    them. Read implies delivered (D20), so both bookmarks move."""
    db.execute(
        update(ChatMember)
        .where(ChatMember.chat_id == chat_id, ChatMember.user_id == sender_id)
        .values(read_up_to=seq, delivered_up_to=seq)
    )


def add_message(
    db: Session,
    chat_id: uuid.UUID,
    sender_id: uuid.UUID,
    client_msg_id: uuid.UUID,
    body: str,
) -> tuple[Message, bool]:
    """Save a message with its chat's next number (#1, #2, #3...).
    Returns (message, created). Sending the same client_msg_id again returns
    (the first copy, False), not a new row (D18).
    Raises NotAMember if the sender has left the chat or was removed."""
    already_sent = _find_sent(db, sender_id, client_msg_id)
    if already_sent is not None:
        return already_sent, False

    seq = take_seq(db, chat_id)
    if seq is None:
        db.rollback()
        raise ValueError(f"No chat with id {chat_id}")

    # Checked here, while this send holds the chat's lock: a removal that was
    # saved first is seen now, and one that comes later waits for this send.
    # So a removed member can never slip a message in after the "removed" note.
    member = db.get(ChatMember, (chat_id, sender_id), populate_existing=True)
    if member is None or not member.current:
        db.rollback()  # undoes the +1, so no number is skipped
        raise NotAMember

    mark_sent(db, chat_id, sender_id, seq)
    message = Message(
        chat_id=chat_id, seq=seq, sender_id=sender_id, client_msg_id=client_msg_id, body=body
    )
    db.add(message)
    try:
        # The +1, the bookmark and the new row are saved together, or not at all.
        db.commit()
    except IntegrityError:
        # The same send arrived twice at once, and the other copy was saved first.
        # Rolling back also undoes our +1, so no number is skipped.
        db.rollback()
        already_sent = _find_sent(db, sender_id, client_msg_id)
        if already_sent is None:
            raise  # refused for some other reason: don't hide it
        return already_sent, False

    return message, True


def add_system_message(db: Session, chat_id: uuid.UUID, actor_id: uuid.UUID, data: dict) -> Message:
    """A group note (D37): "Ana added Ben", "Ben left"... with the chat's next
    number, like any message. It doesn't commit: the caller saves it together
    with the change it describes, in one transaction."""
    seq = take_seq(db, chat_id)
    mark_sent(db, chat_id, actor_id, seq)
    message = Message(
        chat_id=chat_id,
        seq=seq,
        sender_id=actor_id,
        # Made here, since no app sent it. Unique, like every client_msg_id.
        client_msg_id=uuid.uuid4(),
        body="",
        kind="system",
        data=data,
    )
    db.add(message)
    db.flush()  # sends the row now, so it has its id and time
    return message
