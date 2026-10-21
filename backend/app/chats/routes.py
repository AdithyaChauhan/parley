from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.schemas import ChatOut, StartDirectChatRequest
from app.chats.service import get_or_create_direct_chat, list_my_chats
from app.db import get_db

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/direct", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def start_direct_chat(
    body: StartDirectChatRequest,
    response: Response,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
