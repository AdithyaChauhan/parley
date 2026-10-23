import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import anyio.to_thread
import redis
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.schemas import BookmarkIn
from app.chats.service import member_ids, partner_ids, save_bookmark
from app.db import SessionLocal
from app.limits import service as limits
from app.live import bus, manager, tickets
from app.presence import service as presence

log = logging.getLogger(__name__)

router = APIRouter(prefix="/live", tags=["live"])

# The hang-up code for a bad, used or expired ticket (D19). Codes 4000-4999
# are free for apps to use; 4401 echoes HTTP's 401 "not logged in".
BAD_TICKET = 4401
# The standard code for "the server hit a problem": here, Redis went down.
# The app reconnects with its backoff, like after any drop (D21).
SERVER_PROBLEM = 1011

# A second "typing" from the same line this soon after the last one is dropped.
TYPING_GAP_SECONDS = 1


class TicketOut(BaseModel):
    ticket: str
    expires_in: int  # seconds


class EventIn(BaseModel):
    """Anything the app sends on the line: {"type": "...", "data": {...}} (D19)."""

    type: str
    # An event with no data, like {"type": "ping"}, counts as {} (D21).
    data: dict = {}


class LiveBookmarkIn(BookmarkIn):
    """"delivered" or "read" on the live line: the HTTP door's body (seq),
    plus which chat, since a line isn't tied to one chat."""

    chat_id: uuid.UUID


class TypingIn(BaseModel):
    """The person is typing in this chat (D20)."""

    chat_id: uuid.UUID


@dataclass
class _Line:
    """What the server remembers about one open line, while it's open."""

    user_id: uuid.UUID
    # The line itself, for answers that go back only to this tab (pong).
    websocket: WebSocket
    # When this line's last "typing" got through, on the _now() clock. Far in the past at first.
    last_typing: float = float("-inf")
    # One line = one open tab. The server names it, for the presence list (D22).
    tab_id: uuid.UUID = field(default_factory=uuid.uuid4)


def _now() -> float:
    """Seconds on a clock that only moves forward. Tests swap this to fake the time."""
    return time.monotonic()


@router.post("/ticket", response_model=TicketOut)
def new_ticket(me: User = Depends(get_current_user)):
    limits.enforce(limits.TICKET, me.id)
    try:
        ticket = tickets.issue(me.id)
    except redis.RedisError:
        # Tickets and the radio both live in Redis, so without it there is no
        # live line. The app counts this as "line down" and keeps backing off (D24).
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Live updates unavailable")
    return TicketOut(ticket=ticket, expires_in=tickets.TICKET_SECONDS)


def _others(db: Session, chat_id: uuid.UUID, user_id: uuid.UUID) -> list[uuid.UUID]:
    """The other people in this chat. [] if this person isn't in it."""
    members = member_ids(db, chat_id)
    if user_id not in members:
        return []
    return [member for member in members if member != user_id]


# The worker-thread helpers below each open their own short database session:
# a line can stay open for hours, and mustn't hold a connection all that time.


def _save_bookmark(user_id: uuid.UUID, kind: str, bookmark: LiveBookmarkIn) -> None:
    """The same save_bookmark the HTTP door uses (D20): it moves the bookmark
    and, if it moved, pushes the receipt."""
    with SessionLocal() as db:
        save_bookmark(db, bookmark.chat_id, user_id, kind, bookmark.seq)


def _typing_to(user_id: uuid.UUID, chat_id: uuid.UUID) -> list[uuid.UUID]:
    """Who gets this person's "typing": the others in the chat. [] for a non-member."""
    with SessionLocal() as db:
        return _others(db, chat_id, user_id)


def _presence_news(user_id: uuid.UUID) -> tuple[list[uuid.UUID], datetime | None]:
    """Who gets this person's online/offline news (everyone who shares a chat
    with them), and their last seen."""
    with SessionLocal() as db:
        partners = partner_ids(db, user_id)
    return partners, presence.last_seen(user_id)


async def _push_presence(user_id: uuid.UUID, online: bool) -> None:
    """Tell everyone who shares a chat with this person that they just came
    online or went offline, on whichever copy their lines are (D23)."""
    partners, seen = await anyio.to_thread.run_sync(_presence_news, user_id)
    event = {
        "type": "presence",
        "data": {"user_id": str(user_id), "online": online, "last_seen": seen.isoformat() if seen else None},
    }
    await bus.publish_async(partners, event)


async def _tab_alive(line: _Line) -> None:
    """Hello or ping: this tab is still here. Pushes news only if that's a change."""
    if await presence.tab_alive(line.user_id, line.tab_id):
        await _push_presence(line.user_id, online=True)


async def _on_bookmark(line: _Line, event: EventIn) -> None:
    """"delivered" or "read": move the bookmark and, if it moved, send a
    receipt to everyone in the chat, my own tabs too."""
    try:
        bookmark = LiveBookmarkIn.model_validate(event.data)
    except ValidationError:
        return

    # The database code is normal (sync) code (D15), so it runs in a worker
    # thread; the rest of the server keeps going while it waits. The receipt
    # is pushed from there too, with the normal Redis client.
    await anyio.to_thread.run_sync(_save_bookmark, line.user_id, event.type, bookmark)


async def _on_typing(line: _Line, event: EventIn) -> None:
    """"typing": pass it on to the others in the chat. Nothing is saved (D20)."""
    try:
        typing = TypingIn.model_validate(event.data)
    except ValidationError:
        return

    # The app sends at most one every 3 seconds, so a faster line is buggy or
    # spamming. Checked before the database, so spam costs it nothing.
    now = _now()
    if now - line.last_typing < TYPING_GAP_SECONDS:
        return
    line.last_typing = now

    others = await anyio.to_thread.run_sync(_typing_to, line.user_id, typing.chat_id)
    pushed = {"type": "typing", "data": {"chat_id": str(typing.chat_id), "user_id": str(line.user_id)}}
    await bus.publish_async(others, pushed)


async def _handle(line: _Line, text: str) -> None:
    """One event from the app. A broken or unknown event is ignored, so it
    can't knock the line down."""
    try:
        event = EventIn.model_validate_json(text)
    except ValidationError:
        return

    if event.type in ("delivered", "read"):
        await _on_bookmark(line, event)
    elif event.type == "typing":
        await _on_typing(line, event)
    elif event.type == "ping":
        # The app's heartbeat: "are you still there?" (D21). Only this tab gets
        # the answer, and no database is touched, so it costs almost nothing.
        await line.websocket.send_json({"type": "pong", "data": {}})
        # Pong first, so Redis never slows down the heartbeat.
        await _tab_alive(line)


# A missing ticket counts as a bad one, so it also gets 4401.
@router.websocket("")
async def live_line(websocket: WebSocket, ticket: str = ""):
    user_id = await tickets.redeem(ticket)

    # Pick up first, even for a bad ticket: if we refuse before picking up,
    # the browser only sees "failed" (1006) and never our 4401.
    await websocket.accept()
    if user_id is None:
        await websocket.close(code=BAD_TICKET)
        return

    manager.connect(user_id, websocket)
    line = _Line(user_id, websocket)
    try:
        # Listen on the radio for this person first, and wait until Redis
        # confirms (D23): then nothing shouted after hello can be missed.
        await bus.match_lines(user_id)
        # Online next, then hello: by the time the app hears hello, everyone
        # who needed the "came online" news already has it.
        await _tab_alive(line)
        await websocket.send_json({"type": "hello", "data": {"user_id": str(user_id)}})
        # Keep the line open and handle what the app sends, one event at a
        # time. When the tab closes, this raises WebSocketDisconnect.
        while True:
            await _handle(line, await websocket.receive_text())
    except WebSocketDisconnect:
        pass  # the tab closed: a normal ending
    except redis.RedisError:
        # Redis went down (a ping couldn't mark the tab alive). Without it this
        # line can't hear pushes, so end it on purpose; the app reconnects once
        # Redis is back, and catches up by number (D21, D24).
        log.warning("Redis is down, closing a live line")
        await websocket.close(code=SERVER_PROBLEM)
    finally:
        # Runs however the line ends, so a closed tab never stays on the switchboard,
        # on the radio or in the presence list.
        manager.disconnect(user_id, websocket)
        # Shielded: even if the line is being cut off (server shutting down),
        # the goodbye gets up to 5 s to finish. Otherwise the person would look
        # online until their time ran out.
        with anyio.move_on_after(5, shield=True):
            try:
                # Stop listening for them if that was their last tab on this copy.
                await bus.match_lines(user_id)
                if await presence.tab_closed(user_id, line.tab_id):
                    await _push_presence(user_id, online=False)
            except redis.RedisError:
                # Redis is down: the tab's "alive until" time runs out by itself.
                log.warning("Redis is down, skipped a line's goodbye")
