from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.auth.models import User
from app.live import manager, tickets

router = APIRouter(prefix="/live", tags=["live"])

# The hang-up code for a bad, used or expired ticket (D19). Codes 4000-4999
# are free for apps to use; 4401 echoes HTTP's 401 "not logged in".
BAD_TICKET = 4401


class TicketOut(BaseModel):
    ticket: str
    expires_in: int  # seconds


@router.post("/ticket", response_model=TicketOut)
def new_ticket(me: User = Depends(get_current_user)):
    return TicketOut(ticket=tickets.issue(me.id), expires_in=tickets.TICKET_SECONDS)


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
        # Keep the line open. The app sends nothing yet, so we just wait;
        # when the tab closes, this raises WebSocketDisconnect.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass  # the tab closed: a normal ending
    finally:
        # Runs however the line ends, so a closed tab never stays on the switchboard.
        manager.disconnect(user_id, websocket)
