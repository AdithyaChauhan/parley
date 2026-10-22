import uuid

import anyio.to_thread
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.service import mark_delivered, member_ids
from app.db import SessionLocal
from app.live import manager, tickets

router = APIRouter(prefix="/live", tags=["live"])

# The hang-up code for a bad, used or expired ticket (D19). Codes 4000-4999
# are free for apps to use; 4401 echoes HTTP's 401 "not logged in".
BAD_TICKET = 4401


class TicketOut(BaseModel):
    ticket: str
    expires_in: int  # seconds


class EventIn(BaseModel):
    """Anything the app sends on the line: {"type": "...", "data": {...}} (D19)."""

    type: str
    data: dict


class DeliveredIn(BaseModel):
    """The app has every message in this chat up to seq (D20)."""

    chat_id: uuid.UUID
    seq: int = Field(ge=1)


@router.post("/ticket", response_model=TicketOut)
def new_ticket(me: User = Depends(get_current_user)):
    return TicketOut(ticket=tickets.issue(me.id), expires_in=tickets.TICKET_SECONDS)


def _save_delivered(user_id: uuid.UUID, delivered: DeliveredIn) -> tuple[int | None, list[uuid.UUID]]:
    """Moves the bookmark and returns (its new value, the other people in the
    chat). (None, []) if it didn't move. Opens its own short database session:
    a line can stay open for hours, and mustn't hold a connection all that time."""
    with SessionLocal() as db:
        moved = mark_delivered(db, delivered.chat_id, user_id, delivered.seq)
        if moved is None:
            return None, []
        return moved, [member for member in member_ids(db, delivered.chat_id) if member != user_id]


async def _handle(user_id: uuid.UUID, text: str) -> None:
    """One event from the app. A broken or unknown event is ignored, so it
    can't knock the line down."""
    try:
        event = EventIn.model_validate_json(text)
        if event.type != "delivered":
            return  # "read" comes in T18
        delivered = DeliveredIn.model_validate(event.data)
    except ValidationError:
        return

    # The database code is normal (sync) code (D15), so it runs in a worker
    # thread; the rest of the server keeps going while it waits.
    moved, others = await anyio.to_thread.run_sync(_save_delivered, user_id, delivered)
    if moved is not None:
        receipt = {
            "type": "receipt",
            "data": {"chat_id": str(delivered.chat_id), "user_id": str(user_id), "delivered_up_to": moved},
        }
        await manager.send_to_users(others, receipt)


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
    try:
        await websocket.send_json({"type": "hello", "data": {"user_id": str(user_id)}})
        # Keep the line open and handle what the app sends, one event at a
        # time. When the tab closes, this raises WebSocketDisconnect.
        while True:
            await _handle(user_id, await websocket.receive_text())
    except WebSocketDisconnect:
        pass  # the tab closed: a normal ending
    finally:
        # Runs however the line ends, so a closed tab never stays on the switchboard.
        manager.disconnect(user_id, websocket)
