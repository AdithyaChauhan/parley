import uuid

from fastapi import WebSocket

# The switchboard: user id -> that user's open lines on THIS copy, one per tab.
# Each backend copy keeps its own; pushes reach it through the radio (bus.py, D23).
#
# No lock here: only the async side touches this list, and it runs one piece
# of code at a time, switching only at an "await".
lines: dict[uuid.UUID, set[WebSocket]] = {}


def connect(user_id: uuid.UUID, websocket: WebSocket) -> None:
    lines.setdefault(user_id, set()).add(websocket)


def disconnect(user_id: uuid.UUID, websocket: WebSocket) -> None:
    user_lines = lines.get(user_id)
    if user_lines is None:
        return
    user_lines.discard(websocket)
    if not user_lines:
        # That was the user's last tab here: take them off the switchboard.
        del lines[user_id]


async def send_to_user(user_id: uuid.UUID, text: str) -> None:
    """Send an event (already JSON text) to every open tab of this user on this
    copy. A tab whose send fails is dropped, and the other tabs still get it."""
    # A copy: a tab may close while we wait on a send, which changes the set.
    for websocket in list(lines.get(user_id, ())):
        try:
            await websocket.send_text(text)
        except Exception:
            # A dead tab (closed, network gone): take it off the switchboard.
            disconnect(user_id, websocket)
