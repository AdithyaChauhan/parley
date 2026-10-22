import uuid

from fastapi import WebSocket

# The switchboard: user id -> that user's open lines, one per open tab.
# In memory for now; Redis in T21 (D19).
#
# No lock here, unlike tickets.py: only the async side touches this list,
# and it runs one piece of code at a time, switching only at an "await".
# (T17: the send route runs in a worker thread, so it must hand its pushes
# over to the async side instead of calling send_to_user directly.)
lines: dict[uuid.UUID, set[WebSocket]] = {}


def connect(user_id: uuid.UUID, websocket: WebSocket) -> None:
    lines.setdefault(user_id, set()).add(websocket)


def disconnect(user_id: uuid.UUID, websocket: WebSocket) -> None:
    user_lines = lines.get(user_id)
    if user_lines is None:
        return
    user_lines.discard(websocket)
    if not user_lines:
        # That was the user's last tab: take them off the switchboard.
        del lines[user_id]


async def send_to_user(user_id: uuid.UUID, event: dict) -> None:
    """Send an event to every open tab of this user. Used from T17."""
    # A copy: a tab may close while we wait on a send, which changes the set.
    for websocket in list(lines.get(user_id, ())):
        await websocket.send_json(event)
