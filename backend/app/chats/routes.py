import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.schemas import BookmarkIn, BookmarksOut, ChatOut, StartDirectChatRequest
from app.chats.service import get_member, get_or_create_direct_chat, list_my_chats, save_bookmark
from app.db import get_db
from app.limits import service as limits

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/direct", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def start_direct_chat(
    body: StartDirectChatRequest,
    response: Response,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Trying email after email to find out who has an account is "fishing" (D24).
    limits.enforce(limits.START_CHAT, me.id)
    if body.email == me.email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't start a chat with yourself")

    other = db.scalar(select(User).where(User.email == body.email))
    if other is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No account with that email")

    chat, created = get_or_create_direct_chat(db, me, other)
    if not created:
        response.status_code = status.HTTP_200_OK  # the chat already existed
    # The same shape as a row of the chat list, so the app can show it right away.
    return list_my_chats(db, me, chat_id=chat.id)[0]


@router.get("", response_model=list[ChatOut])
def my_chats(me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list_my_chats(db, me)


# The HTTP door for "delivered" and "read" (D20): the app uses it when the
# live line is down, so bookmarks (in PostgreSQL) never depend on Redis.


def _bookmark_door(db: Session, chat_id: uuid.UUID, me: User, kind: Literal["delivered", "read"], seq: int):
    # The same 404 for "no such chat" and "not your chat", as for messages.
    member = get_member(db, chat_id, me.id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")

    # The same function as the live line: same rules, same receipt.
    moved = save_bookmark(db, chat_id, me.id, kind, seq)
    if moved is None:
        # Nothing moved (already there, or further): the bookmarks as they are now.
        # save_bookmark committed, so these are read fresh from the database.
        return BookmarksOut(delivered_up_to=member.delivered_up_to, read_up_to=member.read_up_to)
    return BookmarksOut(delivered_up_to=moved.delivered_up_to, read_up_to=moved.read_up_to)


@router.post("/{chat_id}/delivered", response_model=BookmarksOut)
def delivered(
    chat_id: uuid.UUID, body: BookmarkIn, me: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _bookmark_door(db, chat_id, me, "delivered", body.seq)


@router.post("/{chat_id}/read", response_model=BookmarksOut)
def read(chat_id: uuid.UUID, body: BookmarkIn, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _bookmark_door(db, chat_id, me, "read", body.seq)
