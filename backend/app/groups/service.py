"""Groups (D37): create, add, remove, leave, rename and make admin.

Every change follows the same three steps, in one transaction:
  1. Lock the group's row (the same row that hands out message numbers, D18).
     Two admins changing members at the same moment take turns here.
  2. Check, under that lock, that the person asking may do it. The check sees
     every change saved before ours, so an admin who was just removed can't
     still remove someone else.
  3. Save the change and its system message together. The note takes the
     chat's next number, so numbers stay gap-free.
The routes push the note after the commit, like any message (D9).
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.chats.models import Chat, ChatMember
from app.groups.schemas import MAX_MEMBERS
from app.messages.models import Message
from app.messages.service import add_system_message

ADMIN = "admin"
MEMBER = "member"


def _person(user: User) -> dict:
    """Who did it, or who it was done to, in a note's data. The name is kept
    too, so the app can write the words without looking anyone up."""
    return {"id": str(user.id), "name": user.name}


def _not_found() -> HTTPException:
    # The same 404 for "no such group" and "not your group" (as for messages),
    # so a stranger can't tell whether a chat id is real.
    return HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")


def _lock_group(db: Session, chat_id: uuid.UUID) -> Chat:
    """Step 1: the group's row, locked until the commit. Direct chats have no
    members to change, so they count as "not found"."""
    chat = db.scalar(
        select(Chat).where(Chat.id == chat_id, Chat.kind == "group").with_for_update()
    )
    if chat is None:
        raise _not_found()
    return chat


def _my_row(db: Session, chat_id: uuid.UUID, me: User, admin: bool = False) -> ChatMember:
    """Step 2: my row, read fresh (after the lock), and whether I may act."""
    mine = db.get(ChatMember, (chat_id, me.id), populate_existing=True)
    if mine is None:
        raise _not_found()
    if not mine.current:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You're no longer a member of this group")
    if admin and mine.role != ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only group admins can do that")
    return mine


def _current_row(db: Session, chat_id: uuid.UUID, user_id: uuid.UUID) -> ChatMember:
    """Someone else's row, if they're a current member."""
    row = db.get(ChatMember, (chat_id, user_id), populate_existing=True)
    if row is None or not row.current:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not a member of this group")
    return row


def _current_count(db: Session, chat_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count()).where(ChatMember.chat_id == chat_id, ChatMember.until_seq.is_(None))
    )


def _too_many() -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, f"A group has at most {MAX_MEMBERS} members")


def find_people(db: Session, me: User, user_ids: list[uuid.UUID], emails: list[str]) -> list[User]:
    """The people to add, once each and never me (D37).
    user_ids must be people I have a direct chat with: an id alone isn't a
    way to reach a stranger. Emails must match an account exactly."""
    people: dict[uuid.UUID, User] = {}

    if user_ids:
        my_direct_chats = (
            select(ChatMember.chat_id)
            .join(Chat, Chat.id == ChatMember.chat_id)
            .where(ChatMember.user_id == me.id, Chat.kind == "direct")
        )
        partners = db.scalars(
            select(User)
            .join(ChatMember, ChatMember.user_id == User.id)
            .where(ChatMember.chat_id.in_(my_direct_chats), User.id.in_(user_ids))
        )
        people.update({user.id: user for user in partners})
        if any(user_id not in people and user_id != me.id for user_id in user_ids):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can only add people from your chats, or by email")

    for email in emails:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            # They typed it, so naming it back leaks nothing new (like start-chat).
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"No account with {email}")
        people[user.id] = user

    people.pop(me.id, None)
    return list(people.values())


def create_group(db: Session, me: User, name: str, people: list[User]) -> tuple[Chat, Message]:
    """A new group with me as its admin, and the "created" note as #1.
    Nobody else knows its id yet, so there's nothing to lock."""
    if len(people) + 1 > MAX_MEMBERS:
        raise _too_many()

    chat = Chat(kind="group", title=name)
    db.add(chat)
    db.flush()  # sends the row now, so it has its id for the members
    db.add(ChatMember(chat_id=chat.id, user_id=me.id, role=ADMIN))
    db.add_all(ChatMember(chat_id=chat.id, user_id=person.id) for person in people)
    db.flush()
    note = add_system_message(
        db, chat.id, me.id, {"event": "created", "by": _person(me), "name": name, "users": [_person(p) for p in people]}
    )
    db.commit()
    return chat, note


def add_members(db: Session, chat_id: uuid.UUID, me: User, people: list[User]) -> Message | None:
    """An admin adds people. They see the group from the "added" note on, not
    the earlier history (D37). None if they were all members already."""
    _lock_group(db, chat_id)
    _my_row(db, chat_id, me, admin=True)

    rows = {person.id: db.get(ChatMember, (chat_id, person.id), populate_existing=True) for person in people}
    new = [person for person in people if rows[person.id] is None or not rows[person.id].current]
    if not new:
        return None
    # Counted under the lock, so two admins adding at once can't pass 50 together.
    if _current_count(db, chat_id) + len(new) > MAX_MEMBERS:
        raise _too_many()

    note = add_system_message(db, chat_id, me.id, {"event": "added", "by": _person(me), "users": [_person(p) for p in new]})
    for person in new:
        row = rows[person.id]
        if row is None:
            row = ChatMember(chat_id=chat_id, user_id=person.id)
            db.add(row)
        # Starts at the note. The bookmarks start just before it, so their ticks
        # never hold back older messages they can't see (D37).
        row.role = MEMBER
        row.from_seq = note.seq
        row.until_seq = None
        row.delivered_up_to = row.read_up_to = note.seq - 1
        row.joined_at = func.now()
    db.commit()
    return note


def remove_member(db: Session, chat_id: uuid.UUID, me: User, user_id: uuid.UUID) -> Message:
    """An admin removes someone. They keep what they had, and see the chat
    read-only up to the "removed" note (D37)."""
    _lock_group(db, chat_id)
    _my_row(db, chat_id, me, admin=True)
    if user_id == me.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Use leave to leave the group")
    row = _current_row(db, chat_id, user_id)
    target = db.get(User, user_id)

    note = add_system_message(db, chat_id, me.id, {"event": "removed", "by": _person(me), "users": [_person(target)]})
    row.until_seq = note.seq
    row.role = MEMBER  # an admin removed is no longer an admin
    db.commit()
    return note


def leave(db: Session, chat_id: uuid.UUID, me: User) -> Message:
    """Anyone can leave. If the last admin leaves, the longest-standing member
    becomes admin, in the same note (D37)."""
    _lock_group(db, chat_id)
    mine = _my_row(db, chat_id, me)

    data: dict = {"event": "left", "by": _person(me)}
    successor = None
    if mine.role == ADMIN:
        others = select(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.until_seq.is_(None), ChatMember.user_id != me.id
        )
        other_admin = db.scalar(others.where(ChatMember.role == ADMIN).limit(1))
        if other_admin is None:
            # Longest-standing: the earliest start, then the earliest join.
            successor = db.scalar(others.order_by(ChatMember.from_seq, ChatMember.joined_at).limit(1))
            if successor is not None:
                data["new_admin"] = _person(db.get(User, successor.user_id))

    note = add_system_message(db, chat_id, me.id, data)
    mine.until_seq = note.seq
    mine.role = MEMBER
    if successor is not None:
        successor.role = ADMIN
    db.commit()
    return note


def rename(db: Session, chat_id: uuid.UUID, me: User, name: str) -> Message | None:
    """An admin renames the group. None if the name didn't change."""
    chat = _lock_group(db, chat_id)
    _my_row(db, chat_id, me, admin=True)
    if name == chat.title:
        return None

    chat.title = name
    note = add_system_message(db, chat_id, me.id, {"event": "renamed", "by": _person(me), "name": name})
    db.commit()
    return note


def make_admin(db: Session, chat_id: uuid.UUID, me: User, user_id: uuid.UUID) -> Message | None:
    """An admin makes someone else an admin. None if they already were."""
    _lock_group(db, chat_id)
    _my_row(db, chat_id, me, admin=True)
    row = _current_row(db, chat_id, user_id)
    if row.role == ADMIN:
        return None

    row.role = ADMIN
    target = db.get(User, user_id)
    note = add_system_message(db, chat_id, me.id, {"event": "made_admin", "by": _person(me), "users": [_person(target)]})
    db.commit()
    return note


def members(db: Session, chat_id: uuid.UUID, me: User) -> list[tuple[uuid.UUID, str, str]]:
    """The current members, admins first, then by name: (user id, name, role).
    Only for current members (D37)."""
    if db.scalar(select(Chat.id).where(Chat.id == chat_id, Chat.kind == "group")) is None:
        raise _not_found()
    _my_row(db, chat_id, me)
    rows = db.execute(
        select(ChatMember.user_id, User.name, ChatMember.role)
        .join(User, User.id == ChatMember.user_id)
        .where(ChatMember.chat_id == chat_id, ChatMember.until_seq.is_(None))
        .order_by(ChatMember.role != ADMIN, User.name)
    )
    return [(row.user_id, row.name, row.role) for row in rows]
