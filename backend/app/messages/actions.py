"""Reactions, edit and delete for everyone (D39).

Every change follows the same steps, in one transaction, like a group change (D37):
  1. Lock the chat's row (the one that hands out message numbers, D18), so two
     changes to one message take turns, and a removal can't slip past the check.
  2. Check, under that lock, that this person may do it.
  3. Change the message, and save an event row with the chat's next number, so
     catch-up by number brings the change (D21).
The event row holds only which message changed. The text lives in one place,
the message itself, so deleting it really erases it.
Doing the same thing twice changes nothing and takes no number: a retry is safe.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.chats.models import Chat, ChatMember
from app.files.models import Upload
from app.messages.models import REAL_KINDS, Message, Reaction
from app.messages.service import take_seq

EDIT_WINDOW = timedelta(minutes=15)
DELETE_WINDOW = timedelta(hours=1)


class Change(NamedTuple):
    target: Message
    # The new numbered row. None if nothing actually changed.
    event: Message | None = None
    # A deleted file still to remove from the store, once the commit is done.
    erase: tuple[uuid.UUID, str] | None = None


def _refuse(detail: str, code: int = status.HTTP_403_FORBIDDEN) -> HTTPException:
    return HTTPException(code, detail)


def _not_found() -> HTTPException:
    # The same 404 for "no such message" and "not one you can see", like chats.
    return _refuse("Message not found", status.HTTP_404_NOT_FOUND)


def _locked_target(db: Session, chat_id: uuid.UUID, me_id: uuid.UUID, seq: int) -> Message:
    """Steps 1 and 2: the chat locked, me a current member, and the message one I can see."""
    if db.scalar(select(Chat.id).where(Chat.id == chat_id).with_for_update()) is None:
        raise _not_found()
    member = db.get(ChatMember, (chat_id, me_id), populate_existing=True)
    if member is None:
        raise _not_found()
    if not member.current:
        raise _refuse("You're no longer a member of this group")
    target = db.scalar(
        select(Message).where(Message.chat_id == chat_id, Message.seq == seq, Message.kind.in_(REAL_KINDS))
    )
    # Nothing from before I joined the group (D37).
    if target is None or seq < member.from_seq:
        raise _not_found()
    return target


def _too_late(target: Message, window: timedelta) -> bool:
    return datetime.now(UTC) - target.created_at > window


def _not_deleted(target: Message) -> None:
    if target.deleted_at is not None:
        raise _refuse("This message was deleted", status.HTTP_400_BAD_REQUEST)


def _add_event(db: Session, target: Message, kind: str, actor_id: uuid.UUID) -> Message:
    """Step 3's event: the chat's next number, pointing at the target. It moves
    nobody's bookmarks: reacting to an old message isn't reading the new ones."""
    seq = take_seq(db, target.chat_id)
    event = Message(
        chat_id=target.chat_id,
        seq=seq,
        sender_id=actor_id,
        # Made here, like a group note's: no app sent this row.
        client_msg_id=uuid.uuid4(),
        body="",
        kind=kind,
        data={"target_seq": target.seq},
    )
    db.add(event)
    target.state_seq = seq
    db.flush()  # sends the row now, so it has its id and time
    return event


def set_reaction(db: Session, chat_id: uuid.UUID, me_id: uuid.UUID, seq: int, emoji: str) -> Change:
    """My reaction to this message. Replaces my earlier one (one per person, D39)."""
    target = _locked_target(db, chat_id, me_id, seq)
    _not_deleted(target)
    mine = db.get(Reaction, (target.id, me_id), populate_existing=True)
    if mine is not None and mine.emoji == emoji:
        return Change(target)
    if mine is None:
        db.add(Reaction(message_id=target.id, user_id=me_id, emoji=emoji))
    else:
        mine.emoji = emoji
    event = _add_event(db, target, "reaction", me_id)
    db.commit()
    return Change(target, event)


def remove_reaction(db: Session, chat_id: uuid.UUID, me_id: uuid.UUID, seq: int) -> Change:
    target = _locked_target(db, chat_id, me_id, seq)
    mine = db.get(Reaction, (target.id, me_id), populate_existing=True)
    if mine is None:
        return Change(target)
    db.delete(mine)
    event = _add_event(db, target, "reaction", me_id)
    db.commit()
    return Change(target, event)


def edit_message(db: Session, chat_id: uuid.UUID, me_id: uuid.UUID, seq: int, body: str) -> Change:
    """My own text message, within 15 minutes (D39)."""
    target = _locked_target(db, chat_id, me_id, seq)
    if target.sender_id != me_id:
        raise _refuse("You can only edit your own messages")
    if target.kind != "text":
        raise _refuse("Only text messages can be edited", status.HTTP_400_BAD_REQUEST)
    _not_deleted(target)
    if target.body == body:
        return Change(target)
    if _too_late(target, EDIT_WINDOW):
        raise _refuse("Messages can only be edited for 15 minutes")
    target.body = body
    target.edited_at = datetime.now(UTC)
    event = _add_event(db, target, "edit", me_id)
    db.commit()
    return Change(target, event)


def delete_message(db: Session, chat_id: uuid.UUID, me_id: uuid.UUID, seq: int) -> Change:
    """My own message, within 1 hour, for everyone (D39): the text, the file's
    details and the reactions go here, and the file itself right after the commit."""
    target = _locked_target(db, chat_id, me_id, seq)
    if target.sender_id != me_id:
        raise _refuse("You can only delete your own messages")
    if target.deleted_at is not None:
        return Change(target)
    if _too_late(target, DELETE_WINDOW):
        raise _refuse("Messages can only be deleted for 1 hour")

    erase = None
    upload = db.scalar(select(Upload).where(Upload.message_id == target.id))
    if upload is not None:
        # Freed from the message, so no download link can be made for it now.
        # Its name goes too. The key is only ids.
        upload.message_id = None
        upload.name = ""
        upload.erase_pending = True
        erase = (upload.id, upload.key)

    target.body = ""
    target.data = None
    target.deleted_at = datetime.now(UTC)
    db.execute(delete(Reaction).where(Reaction.message_id == target.id))
    event = _add_event(db, target, "delete", me_id)
    db.commit()
    return Change(target, event, erase)


def reactions_of(db: Session, message_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, list[uuid.UUID]]]:
    """Each message's reactions: emoji → who. The app gets the counts from the
    lists, and sees whether one of them is me."""
    found: dict[uuid.UUID, dict[str, list[uuid.UUID]]] = {}
    if message_ids:
        for row in db.scalars(select(Reaction).where(Reaction.message_id.in_(message_ids))):
            found.setdefault(row.message_id, {}).setdefault(row.emoji, []).append(row.user_id)
    return found
