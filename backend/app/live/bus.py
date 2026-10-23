import asyncio
import json
import logging
import uuid

import redis
import redis.asyncio

from app.live import manager

# The Redis clients made in T20 (D22). Used as presence.client and
# presence.async_client, because the async one is only made when the app starts.
from app.presence import service as presence

log = logging.getLogger(__name__)

# How long a new line waits for Redis to confirm "you're listening now".
SUBSCRIBE_WAIT_SECONDS = 5

# The radio (D23). Every push is shouted on user:<id>, and every copy hands what
# it hears to its own open lines. This copy listens on user:<id> only while
# that person has a line here.
#
# All of these are made in start(), inside the server's event loop, like the
# async client: they only work in the loop they were made in.
#
# One Redis connection in "listening mode", shared by every line on this copy.
_pubsub: redis.asyncio.client.PubSub | None = None
# Channels this copy listens on right now.
_listening: set[str] = set()
# Channel -> "Redis confirmed it": set by listen() when the confirmation arrives.
_confirmed: dict[str, asyncio.Event] = {}
# One subscription change at a time (see match_lines).
_lock: asyncio.Lock | None = None


def _channel(user_id: uuid.UUID) -> str:
    return f"user:{user_id}"


async def start() -> None:
    global _pubsub, _lock
    _pubsub = presence.async_client.pubsub()
    # Open the connection now, so listen() can start reading before anyone subscribes.
    await _pubsub.connect()
    _listening.clear()
    _confirmed.clear()
    _lock = asyncio.Lock()


async def stop() -> None:
    await _pubsub.aclose()


def publish(user_ids: list[uuid.UUID], event: dict) -> None:
    """Shout this event to these people, wherever their lines are. For normal
    (def) routes. Never raises: the message is already saved, so a failed push
    must not fail the send (D20); catch-up makes up for it (D21)."""
    text = json.dumps(event)
    try:
        # A pipeline sends every shout in one trip to Redis.
        with presence.client.pipeline(transaction=False) as pipe:
            for user_id in user_ids:
                pipe.publish(_channel(user_id), text)
            pipe.execute()
    except redis.RedisError:
        log.exception("Live push failed")


async def publish_async(user_ids: list[uuid.UUID], event: dict) -> None:
    """The same, for the live line. Never raises, for the same reason."""
    text = json.dumps(event)
    try:
        async with presence.async_client.pipeline(transaction=False) as pipe:
            for user_id in user_ids:
                pipe.publish(_channel(user_id), text)
            await pipe.execute()
    except redis.RedisError:
        log.exception("Live push failed")


async def match_lines(user_id: uuid.UUID) -> None:
    """Listen on user:<id> exactly while this person has a line on this copy.
    Called after a line opens and after one closes.

    The lock and "look at the lines right now": if Ben's last tab closes while
    a new one opens, the two calls can't cross and leave this copy deaf to Ben.
    Whichever runs second sees the true state and fixes it."""
    channel = _channel(user_id)
    async with _lock:
        has_lines = user_id in manager.lines
        if has_lines and channel not in _listening:
            confirmed = _confirmed[channel] = asyncio.Event()
            await _pubsub.subscribe(channel)
            # Wait for Redis's "subscribed", so nothing shouted right after this
            # line's hello is missed. If it never comes, carry on: catch-up covers it.
            try:
                await asyncio.wait_for(confirmed.wait(), SUBSCRIBE_WAIT_SECONDS)
            except TimeoutError:
                log.warning("No subscribe confirmation for %s", channel)
            _listening.add(channel)
        elif not has_lines and channel in _listening:
            await _pubsub.unsubscribe(channel)
            _listening.discard(channel)


async def _deliver(message: dict) -> None:
    """One thing heard on the radio."""
    if message["type"] == "subscribe":
        # Redis confirms a subscription: wake up the line waiting for it.
        confirmed = _confirmed.pop(message["channel"], None)
        if confirmed is not None:
            confirmed.set()
        return
    if message["type"] != "message":
        return  # unsubscribe confirmations and the like

    user_id = uuid.UUID(message["channel"].removeprefix("user:"))
    text = message["data"]
    # Only real events {"type": ..., "data": ...} reach the apps.
    event = json.loads(text)
    if not isinstance(event, dict) or "type" not in event:
        raise ValueError("not an event")
    await manager.send_to_user(user_id, text)


async def listen() -> None:
    """Runs in the background for the copy's whole life (main.py): hands
    everything it hears to this copy's own lines."""
    while True:
        try:
            # Waits until Redis sends something: an event or a confirmation.
            message = await _pubsub.get_message(timeout=None)
        except redis.RedisError:
            # Redis dropped. Wait a moment and listen again: redis-py reconnects
            # and subscribes to every channel again by itself.
            log.warning("Lost Redis, listening again in 1 s")
            await asyncio.sleep(1)
            continue

        if message is None:
            continue
        try:
            await _deliver(message)
        except Exception:
            # A bad event is skipped, and the radio keeps going for everyone else.
            log.exception("Skipped a bad live event")
