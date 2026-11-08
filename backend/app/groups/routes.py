import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.schemas import ChatOut
from app.chats.service import group_low, group_receipt, list_my_chats, member_ids
from app.db import SessionLocal
from app.groups import service
from app.groups.schemas import CreateGroupRequest, GroupMemberOut, PeopleIn, RenameGroupRequest
from app.limits import service as limits
from app.live import bus
from app.messages.models import Message
from app.messages.schemas import MessageOut

router = APIRouter(prefix="/chats", tags=["groups"])


def _limit_emails(me: User, body: PeopleIn) -> None:
    # Each email is one look-up, counted like a start-chat, so a group can't
    # be used to fish for accounts faster (D24). Before any connection is
    # taken, so Redis never holds one (D34).
    for _ in body.emails:
        limits.enforce(limits.START_CHAT, me.id)


def _note_out(db: Session, note: Message | None, me: User) -> list[tuple[list[uuid.UUID], dict]]:
    """What to push after a change: the saved note, to everyone who can see
    its number, so a removed person still hears they were removed (D37).
    Then the group's lowest bookmarks to the current members: a change can
    lift them (someone who was behind left, or the note moved my bookmarks),
    and changes are rare, so it always goes. Read before the session closes."""
    if note is None:
        return []
    event = {"type": "message.new", "data": MessageOut.of(note, me.name).model_dump(mode="json")}
    pushes = [(member_ids(db, note.chat_id, note.seq), event)]
    low = group_low(db, note.chat_id)
    if low is not None:
        pushes.append((member_ids(db, note.chat_id), group_receipt(note.chat_id, low)))
    return pushes


def _push(pushes: list[tuple[list[uuid.UUID], dict]]) -> None:
    # After the commit and with the connection back (D9, D34). Never raises.
    # Group notes don't notify (only real messages do, D39's direction).
    for to, event in pushes:
        bus.publish(to, event)


def _members_out(db: Session, chat_id: uuid.UUID, me: User) -> list[GroupMemberOut]:
    return [
        GroupMemberOut(user_id=user_id, name=name, role=role)
        for user_id, name, role in service.members(db, chat_id, me)
    ]


@router.post("/groups", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def create_group(body: CreateGroupRequest, me: User = Depends(get_current_user)):
    limits.enforce(limits.GROUP_CREATE, me.id)
    _limit_emails(me, body)
    with SessionLocal() as db:
        people = service.find_people(db, me, body.user_ids, body.emails)
        chat, note = service.create_group(db, me, body.name, people)
        pushes = _note_out(db, note, me)
        row = list_my_chats(db, me, chat_id=chat.id)[0]  # closes the session
    _push(pushes)
    # The same shape as a row of the chat list, so the app can show it right away.
    return row


@router.get("/{chat_id}/members", response_model=list[GroupMemberOut])
def list_members(chat_id: uuid.UUID, me: User = Depends(get_current_user)):
    with SessionLocal() as db:
        return _members_out(db, chat_id, me)


@router.post("/{chat_id}/members", response_model=list[GroupMemberOut])
def add_members(chat_id: uuid.UUID, body: PeopleIn, me: User = Depends(get_current_user)):
    limits.enforce(limits.GROUP_CHANGE, me.id)
    _limit_emails(me, body)
    with SessionLocal() as db:
        people = service.find_people(db, me, body.user_ids, body.emails)
        note = service.add_members(db, chat_id, me, people)
        pushes = _note_out(db, note, me)
        members = _members_out(db, chat_id, me)
    _push(pushes)
    return members


@router.delete("/{chat_id}/members/{user_id}", response_model=list[GroupMemberOut])
def remove_member(chat_id: uuid.UUID, user_id: uuid.UUID, me: User = Depends(get_current_user)):
    limits.enforce(limits.GROUP_CHANGE, me.id)
    with SessionLocal() as db:
        note = service.remove_member(db, chat_id, me, user_id)
        pushes = _note_out(db, note, me)
        members = _members_out(db, chat_id, me)
    _push(pushes)
    return members


@router.post("/{chat_id}/members/{user_id}/admin", response_model=list[GroupMemberOut])
def make_admin(chat_id: uuid.UUID, user_id: uuid.UUID, me: User = Depends(get_current_user)):
    limits.enforce(limits.GROUP_CHANGE, me.id)
    with SessionLocal() as db:
        note = service.make_admin(db, chat_id, me, user_id)
        pushes = _note_out(db, note, me)
        members = _members_out(db, chat_id, me)
    _push(pushes)
    return members


@router.post("/{chat_id}/leave", response_model=ChatOut)
def leave(chat_id: uuid.UUID, me: User = Depends(get_current_user)):
    limits.enforce(limits.GROUP_CHANGE, me.id)
    with SessionLocal() as db:
        note = service.leave(db, chat_id, me)
        pushes = _note_out(db, note, me)
        row = list_my_chats(db, me, chat_id=chat_id)[0]
    _push(pushes)
    # My row, now read-only (left: true).
    return row


@router.patch("/{chat_id}", response_model=ChatOut)
def rename(chat_id: uuid.UUID, body: RenameGroupRequest, me: User = Depends(get_current_user)):
    limits.enforce(limits.GROUP_CHANGE, me.id)
    with SessionLocal() as db:
        note = service.rename(db, chat_id, me, body.name)
        pushes = _note_out(db, note, me)
        row = list_my_chats(db, me, chat_id=chat_id)[0]
    _push(pushes)
    return row
