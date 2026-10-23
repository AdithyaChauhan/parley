import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.models import ChatMember
from app.chats.service import get_member, member_ids
from app.db import get_db
from app.live import bus
from app.messages.models import Message
from app.messages.schemas import MemberOut, MessageOut, MessagePage, SendMessageRequest
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
    if created:
        # Saved first (D9), then shouted to everyone in the chat, my other tabs
        # too (D20), on whichever copy their lines are (D23).
        event = {"type": "message.new", "data": MessageOut.model_validate(message).model_dump(mode="json")}
        bus.publish(member_ids(db, chat_id), event)
    else:
        # A resend: here is the first copy. It pushes nothing; the first copy was already pushed.
        response.status_code = status.HTTP_200_OK
    return message


@router.get("", response_model=MessagePage)
def message_history(
    chat_id: uuid.UUID,
    # Only messages numbered below this. Leave both out for the newest page.
    before: int | None = Query(default=None, ge=1),
    # Only messages numbered above this. 0 = from #1 (an empty chat on screen).
    after: int | None = Query(default=None, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
    me: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if before is not None and after is not None:
        # Back and forward at once makes no sense: refused like any other bad query.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Use before or after, not both")
    _check_member(db, chat_id, me)

    query = select(Message).where(Message.chat_id == chat_id)
    if after is not None:
        # Catching up (D21): the ones above my highest number, oldest first,
        # so they come in reading order and I can ask again from the last one.
        query = query.where(Message.seq > after).order_by(Message.seq.asc())
    elif before is not None:
        # Scrolling up: the ones above the oldest on screen, newest first.
        query = query.where(Message.seq < before).order_by(Message.seq.desc())
    else:
        # Opening the chat: the newest ones, newest first.
        query = query.order_by(Message.seq.desc())
    # One extra: if the extra comes back, there are more past these.
    rows = list(db.scalars(query.limit(limit + 1)))

    members = db.scalars(select(ChatMember).where(ChatMember.chat_id == chat_id))
    return MessagePage(
        messages=[MessageOut.model_validate(row) for row in rows[:limit]],
        has_more=len(rows) > limit,
        members=[MemberOut.model_validate(member) for member in members],
    )
