import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import metrics
from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.models import Chat, ChatMember
from app.chats.service import Bookmarks, get_member, low_moved, member_ids
from app.db import SessionLocal
from app.files.cleanup import erase_now
from app.limits import service as limits
from app.live import bus
from app.messages import actions
from app.messages.models import EVENT_KINDS, Message
from app.messages.schemas import (
    EditMessageRequest,
    MemberOut,
    MessageOut,
    MessagePage,
    ReactionRequest,
    SendMessageRequest,
)
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


def _name_of(db: Session, user_id: uuid.UUID) -> str:
    return db.scalar(select(User.name).where(User.id == user_id)) or ""


def _finish_change(db: Session, change: actions.Change, me: User) -> MessageOut:
    """The changed message for the reply, and the event pushed like any message
    (D39). Events never notify, and move nobody's bookmarks."""
    target_id = change.target.id
    target = MessageOut.of(
        change.target,
        _name_of(db, change.target.sender_id),
        actions.reactions_of(db, [target_id]).get(target_id),
    )
    pushes = []
    if change.event is not None:
        event = MessageOut.of(change.event, me.name, target=target)
        viewers = db.execute(
            select(ChatMember.user_id, ChatMember.from_seq).where(
                ChatMember.chat_id == event.chat_id,
                ChatMember.user_id.in_(member_ids(db, event.chat_id, event.seq)),
            )
        ).all()
        # Someone who joined after this message gets the number, but not the
        # message: they aren't allowed to see it (D37).
        can_see = [row.user_id for row in viewers if row.from_seq <= target.seq]
        cannot = [row.user_id for row in viewers if row.from_seq > target.seq]
        pushes.append((can_see, event))
        if cannot:
            pushes.append((cannot, event.model_copy(update={"target": None})))
    db.close()  # back in the pool before the pushes (D34)
    for people, event in pushes:
        bus.publish(people, {"type": "message.new", "data": event.model_dump(mode="json")})
    return target


# The route's number must be a real one (seq starts at 1).
Seq = Annotated[int, Path(ge=1)]


@router.put("/{seq}/reaction", response_model=MessageOut)
def react(chat_id: uuid.UUID, seq: Seq, body: ReactionRequest, me: User = Depends(get_current_user)):
    # Each change takes a number and a push, like a send, so it shares the send limit (D24).
    limits.enforce(limits.SEND, me.id)
    with SessionLocal() as db:
        return _finish_change(db, actions.set_reaction(db, chat_id, me.id, seq, body.emoji), me)


@router.delete("/{seq}/reaction", response_model=MessageOut)
def unreact(chat_id: uuid.UUID, seq: Seq, me: User = Depends(get_current_user)):
    limits.enforce(limits.SEND, me.id)
    with SessionLocal() as db:
        return _finish_change(db, actions.remove_reaction(db, chat_id, me.id, seq), me)


@router.patch("/{seq}", response_model=MessageOut)
def edit(chat_id: uuid.UUID, seq: Seq, body: EditMessageRequest, me: User = Depends(get_current_user)):
    limits.enforce(limits.SEND, me.id)
    with SessionLocal() as db:
        return _finish_change(db, actions.edit_message(db, chat_id, me.id, seq, body.body), me)


@router.delete("/{seq}", response_model=MessageOut)
def delete_for_everyone(chat_id: uuid.UUID, seq: Seq, me: User = Depends(get_current_user)):
    limits.enforce(limits.SEND, me.id)
    with SessionLocal() as db:
        change = actions.delete_message(db, chat_id, me.id, seq)
        result = _finish_change(db, change, me)
    # After the push, and outside the session: a slow store can't hold anything up (D34).
    if change.erase is not None:
        erase_now(*change.erase)
    return result


def _page_messages(db: Session, rows: list, member: ChatMember) -> list[MessageOut]:
    """A page's rows, with the latest state applied. Only catch-up pages have
    event rows, and each one carries the message it changed."""
    events = [message.data["target_seq"] for message, _ in rows if message.kind in EVENT_KINDS]
    # Nothing from before I joined (D37): those events go out with no target.
    wanted = {seq for seq in events if seq >= member.from_seq}
    targets: dict[int, tuple[Message, str]] = {}
    if wanted:
        found = db.execute(
            select(Message, User.name)
            .join(User, User.id == Message.sender_id)
            .where(Message.chat_id == member.chat_id, Message.seq.in_(wanted))
        )
        targets = {message.seq: (message, name) for message, name in found}

    ids = [message.id for message, _ in rows] + [message.id for message, _ in targets.values()]
    reactions = actions.reactions_of(db, ids)

    def out(message: Message, name: str) -> MessageOut:
        target = None
        if message.kind in EVENT_KINDS and message.data["target_seq"] in targets:
            shown, shown_name = targets[message.data["target_seq"]]
            target = MessageOut.of(shown, shown_name, reactions.get(shown.id))
        return MessageOut.of(message, name, reactions.get(message.id), target)

    return [out(message, name) for message, name in rows]


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
        # Events too: this is how a change made while I was away reaches me (D39).
        query = query.where(Message.seq > after).order_by(Message.seq.asc())
    elif before is not None:
        # Scrolling up: the ones above the oldest on screen, newest first.
        query = query.where(Message.seq < before, Message.kind.not_in(EVENT_KINDS)).order_by(Message.seq.desc())
    else:
        # Opening the chat: the newest ones, newest first.
        query = query.where(Message.kind.not_in(EVENT_KINDS)).order_by(Message.seq.desc())
    with SessionLocal() as db:
        member = _member(db, chat_id, me)
        # Read before the messages: a number is only handed out with its row,
        # so every event up to this one is already in what the query below reads.
        newest = db.scalar(select(Chat.last_seq).where(Chat.id == chat_id))
        # Only my stretch of the chat (D37): nothing from before I was added,
        # nothing after I left. A direct chat is from #1, with no end.
        query = query.where(Message.seq >= member.from_seq)
        if not member.current:
            query = query.where(Message.seq <= member.until_seq)
        # One extra: if the extra comes back, there are more past these.
        rows = list(db.execute(query.limit(limit + 1)))
        page = rows[:limit]

        low_seq = high_seq = None
        if page:
            if after is not None:
                low_seq, high_seq = max(after + 1, member.from_seq), page[-1][0].seq
            elif before is not None:
                low_seq, high_seq = page[-1][0].seq, before - 1
            else:
                end = newest if member.current else min(newest, member.until_seq)
                low_seq, high_seq = page[-1][0].seq, max(end, page[0][0].seq)

        members = db.scalars(
            select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.until_seq.is_(None))
        )
        return MessagePage(
            messages=_page_messages(db, page, member),
            low_seq=low_seq,
            high_seq=high_seq,
            has_more=len(rows) > limit,
            members=[MemberOut.model_validate(member) for member in members],
        )
