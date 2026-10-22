import time
import uuid
from dataclasses import dataclass

import anyio.to_thread
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.service import Bookmarks, mark_delivered, mark_read, member_ids
from app.db import SessionLocal
from app.live import manager, tickets

router = APIRouter(prefix="/live", tags=["live"])

# The hang-up code for a bad, used or expired ticket (D19). Codes 4000-4999
# are free for apps to use; 4401 echoes HTTP's 401 "not logged in".
BAD_TICKET = 4401

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


class BookmarkIn(BaseModel):
    """"delivered": the app has every message in this chat up to seq.
    "read": it has shown them on screen, in an open chat, in front (D20)."""

    chat_id: uuid.UUID
    seq: int = Field(ge=1)


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


def _now() -> float:
    """Seconds on a clock that only moves forward. Tests swap this to fake the time."""
    return time.monotonic()


@router.post("/ticket", response_model=TicketOut)
def new_ticket(me: User = Depends(get_current_user)):
    return TicketOut(ticket=tickets.issue(me.id), expires_in=tickets.TICKET_SECONDS)


def _others(db: Session, chat_id: uuid.UUID, user_id: uuid.UUID) -> list[uuid.UUID]:
    """The other people in this chat. [] if this person isn't in it."""
    members = member_ids(db, chat_id)
    if user_id not in members:
        return []
    return [member for member in members if member != user_id]


# The worker-thread helpers below each open their own short database session:
# a line can stay open for hours, and mustn't hold a connection all that time.


def _save_bookmark(user_id: uuid.UUID, kind: str, bookmark: BookmarkIn) -> tuple[Bookmarks | None, list[uuid.UUID]]:
    """Moves the "delivered" or "read" bookmark and returns (both bookmarks,
    everyone in the chat). (None, []) if it didn't move."""
    mark = mark_read if kind == "read" else mark_delivered
    with SessionLocal() as db:
        moved = mark(db, bookmark.chat_id, user_id, bookmark.seq)
        if moved is None:
            return None, []
        # Everyone, me too: my other tabs need my new read_up_to for their unread count (D20).
        # It moved, so I'm a member: no stranger gets the receipt.
        return moved, member_ids(db, bookmark.chat_id)


def _typing_to(user_id: uuid.UUID, chat_id: uuid.UUID) -> list[uuid.UUID]:
    """Who gets this person's "typing": the others in the chat. [] for a non-member."""
    with SessionLocal() as db:
        return _others(db, chat_id, user_id)


async def _on_bookmark(line: _Line, event: EventIn) -> None:
    """"delivered" or "read": move the bookmark and, if it moved, send a
    receipt to everyone in the chat, my own tabs too."""
    try:
        bookmark = BookmarkIn.model_validate(event.data)
    except ValidationError:
        return

    # The database code is normal (sync) code (D15), so it runs in a worker
    # thread; the rest of the server keeps going while it waits.
    moved, everyone = await anyio.to_thread.run_sync(_save_bookmark, line.user_id, event.type, bookmark)
    if moved is not None:
        # Both bookmarks, so the app can pick grey or teal ticks (D20).
        receipt = {
            "type": "receipt",
            "data": {
                "chat_id": str(bookmark.chat_id),
                "user_id": str(line.user_id),
                "delivered_up_to": moved.delivered_up_to,
                "read_up_to": moved.read_up_to,
            },
        }
        await manager.send_to_users(everyone, receipt)


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
    await manager.send_to_users(others, pushed)


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


# A missing ticket counts as a bad one, so it also gets 4401.
@router.websocket("")
async def live_line(websocket: WebSocket, ticket: str = ""):
    user_id = tickets.redeem(ticket)

    # Pick up first, even for a bad ticket: if we refuse before picking up,
    # the browser only sees "failed" (1006) and never our 4401.
    await websocket.accept()
    if user_id is None:
        await websocket.close(code=BAD_TICKET)
        return

    manager.connect(user_id, websocket)
    line = _Line(user_id, websocket)
    try:
        await websocket.send_json({"type": "hello", "data": {"user_id": str(user_id)}})
        # Keep the line open and handle what the app sends, one event at a
        # time. When the tab closes, this raises WebSocketDisconnect.
        while True:
            await _handle(line, await websocket.receive_text())
    except WebSocketDisconnect:
        pass  # the tab closed: a normal ending
    finally:
        # Runs however the line ends, so a closed tab never stays on the switchboard.
        manager.disconnect(user_id, websocket)
