import json
import logging
import uuid

import anyio.from_thread
from fastapi import WebSocket

log = logging.getLogger(__name__)

# The switchboard: user id -> that user's open lines, one per open tab.
# Each backend copy keeps its own; Redis pub/sub links them in T21 (D19).
#
# No lock here, unlike tickets.py: only the async side touches this list,
# and it runs one piece of code at a time, switching only at an "await".
# Normal (def) routes run in a worker thread, so they push with
# push_from_thread, which hands the work over to the async side.
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
    """Send an event to every open tab of this user. A tab whose send fails
    is dropped, and the other tabs still get the event."""
    # Turned into text once, before the loop, so a mistake in the event
    # itself raises here instead of being blamed on the tabs.
    text = json.dumps(event)
    # A copy: a tab may close while we wait on a send, which changes the set.
    for websocket in list(lines.get(user_id, ())):
        try:
            await websocket.send_text(text)
        except Exception:
            # A dead tab (closed, network gone): take it off the switchboard.
            disconnect(user_id, websocket)


async def send_to_users(user_ids: list[uuid.UUID], event: dict) -> None:
    for user_id in user_ids:
        await send_to_user(user_id, event)


def push_from_thread(user_ids: list[uuid.UUID], event: dict) -> None:
    """For normal (def) routes, which run in a worker thread: hand the push
    over to the async side and wait until it's done. Never raises: the
    message is already saved, so a failed push must not fail the send (D20)."""
    try:
        anyio.from_thread.run(send_to_users, user_ids, event)
    except Exception:
        log.exception("Live push failed")
