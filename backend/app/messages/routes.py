import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.service import get_member
from app.db import get_db
from app.messages.models import Message
from app.messages.schemas import MessageOut, MessagePage, SendMessageRequest
from app.messages.service import add_message

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["messages"])


def _check_member(db: Session, chat_id: uuid.UUID, me: User) -> None:
    # The same 404 for "no such chat" and "not your chat", so a stranger
    # can't tell whether a chat id is real.
    if get_member(db, chat_id, me.id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    chat_id: uuid.UUID,
    body: SendMessageRequest,
    response: Response,
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_member(db, chat_id, me)

    message, created = add_message(db, chat_id, me.id, body.client_msg_id, body.body)
    if not created:
        response.status_code = status.HTTP_200_OK  # a resend: here is the first copy
    return message


@router.get("", response_model=MessagePage)
def message_history(
    chat_id: uuid.UUID,
    # Only messages numbered below this. Leave it out for the newest page.
    before: int | None = Query(default=None, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_member(db, chat_id, me)

    query = select(Message).where(Message.chat_id == chat_id)
    if before is not None:
        query = query.where(Message.seq < before)
    # Newest first, and one extra: if the extra comes back, there are older messages.
    rows = list(db.scalars(query.order_by(Message.seq.desc()).limit(limit + 1)))

    return MessagePage(
        messages=[MessageOut.model_validate(row) for row in rows[:limit]],
        has_more=len(rows) > limit,
    )
