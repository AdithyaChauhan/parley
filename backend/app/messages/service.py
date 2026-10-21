import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.chats.models import Chat, ChatMember
from app.messages.models import Message


def _find_sent(db: Session, sender_id: uuid.UUID, client_msg_id: uuid.UUID) -> Message | None:
    return db.scalar(
        select(Message).where(
            Message.sender_id == sender_id, Message.client_msg_id == client_msg_id
        )
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
    (the first copy, False), not a new row (D18)."""
    already_sent = _find_sent(db, sender_id, client_msg_id)
    if already_sent is not None:
        return already_sent, False

    # Take the next number. This UPDATE locks the chat's row until we commit,
    # so another sender to the same chat waits here, then gets the number after ours.
    seq = db.scalar(
        update(Chat)
        .where(Chat.id == chat_id)
        .values(last_seq=Chat.last_seq + 1)
        .returning(Chat.last_seq)
    )
    if seq is None:
        db.rollback()
        raise ValueError(f"No chat with id {chat_id}")

    # The sender has read their own message, so it never counts as unread for them.
    db.execute(
        update(ChatMember)
        .where(ChatMember.chat_id == chat_id, ChatMember.user_id == sender_id)
        .values(read_up_to=seq)
    )

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
