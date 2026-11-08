import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import metrics
from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.models import ChatMember
from app.chats.service import Bookmarks, get_member, low_moved, member_ids
from app.db import SessionLocal
from app.limits import service as limits
from app.live import bus
from app.messages.models import Message
from app.messages.schemas import MemberOut, MessageOut, MessagePage, SendMessageRequest
from app.messages.service import NotAMember, UploadTaken, add_message
from app.notify import publisher as notify

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["messages"])


def _member(db: Session, chat_id: uuid.UUID, me: User) -> ChatMember:
    # The same 404 for "no such chat" and "not your chat", so a stranger
    # can't tell whether a chat id is real. A past member is still "in" the
    # chat, read-only (D37).
    member = get_member(db, chat_id, me.id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return member


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    chat_id: uuid.UUID,
    body: SendMessageRequest,
    response: Response,
    me: User = Depends(get_current_user),
):
    # First, so a flood of sends is turned away before it touches the database (D24).
    limits.enforce(limits.SEND, me.id)
    return save_and_push(chat_id, me, response, body.client_msg_id, body.body)


def save_and_push(
    chat_id: uuid.UUID,
    me: User,
    response: Response,
    client_msg_id: uuid.UUID,
    body: str,
    kind: str = "text",
    data: dict | None = None,
    upload_id: uuid.UUID | None = None,
) -> MessageOut:
    """Save one message, then tell everyone. Texts and files both end up here."""
    with SessionLocal() as db:
        mine = _member(db, chat_id, me)
        # My bookmarks before this send moves them to its number (D20)
        before = Bookmarks(mine.delivered_up_to, mine.read_up_to)

        try:
            saved, created = add_message(db, chat_id, me.id, client_msg_id, body, kind, data, upload_id)
        except NotAMember:
            # Left or removed: the chat is read-only for them now (D37).
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You're no longer a member of this group")
        except UploadTaken:
            raise HTTPException(status.HTTP_409_CONFLICT, "This file was already sent")
        # Everything the reply and the pushes need, read now. After the commit,
        # reading the row loads it again in a new transaction (expire_on_commit),
        # and that holds the connection until the session closes.
        message = MessageOut.of(saved, me.name)
        # Everyone who can see this number: the current members (D37).
        members = member_ids(db, chat_id, message.seq) if created else []
        # Sending counts as reading (D20): in a group, if I was the one holding
        # the ticks back, everyone gets the new lowest (D37).
        lifted = low_moved(db, chat_id, before) if created else None

    # The connection is back in the pool, so slow pushes can't hold it (D34).
    if created:
        metrics.MESSAGES_SENT.inc()
        # Saved first (D9), then shouted to everyone in the chat, my other tabs
        # too (D20), on whichever copy their lines are (D23). In a group, one
        # shout per member (D37).
        bus.publish(members, {"type": "message.new", "data": message.model_dump(mode="json")})
        # And a "notify them if they don't read it" job for everyone but me (D25).
        notify.publish(message, [user_id for user_id in members if user_id != me.id])
        if lifted is not None:
            bus.publish(*lifted)
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
):
    if before is not None and after is not None:
        # Back and forward at once makes no sense: refused like any other bad query.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Use before or after, not both")

    query = select(Message, User.name).join(User, User.id == Message.sender_id).where(Message.chat_id == chat_id)
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
    with SessionLocal() as db:
        member = _member(db, chat_id, me)
        # Only my stretch of the chat (D37): nothing from before I was added,
        # nothing after I left. A direct chat is from #1, with no end.
        query = query.where(Message.seq >= member.from_seq)
        if not member.current:
            query = query.where(Message.seq <= member.until_seq)
        # One extra: if the extra comes back, there are more past these.
        rows = list(db.execute(query.limit(limit + 1)))

        members = db.scalars(
            select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.until_seq.is_(None))
        )
        return MessagePage(
            messages=[MessageOut.of(message, name) for message, name in rows[:limit]],
            has_more=len(rows) > limit,
            members=[MemberOut.model_validate(member) for member in members],
        )
