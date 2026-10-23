import logging
import time
import uuid
from datetime import UTC, datetime
from typing import NamedTuple

import redis
import redis.asyncio
import redis.asyncio.retry
import redis.retry
from redis.backoff import NoBackoff

from app.config import settings

log = logging.getLogger(__name__)

# A tab counts as alive for this long after its last ping. The app pings every
# 25 s (D21), so a living tab always pings again in time, even if one is lost.
ALIVE_SECONDS = 60

# Give up fast when Redis is down (D24). Out of the box the client tries 10
# times with growing waits: one call took 49 s. Now: at most 1 s to connect.
CONNECT_SECONDS = 1


def new_client(url: str) -> redis.Redis:
    """The normal client, for normal (def) routes like the chat list.
    decode_responses: answers come back as text, not raw bytes.
    One try only: a send waits for it. After a Redis restart, this client
    swaps a dead connection for a fresh one by itself, so no second try is needed."""
    return redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=CONNECT_SECONDS,
        retry=redis.retry.Retry(NoBackoff(), 0),
    )


def new_async_client(url: str) -> redis.asyncio.Redis:
    """The async one, for the live line. One quick second try: after a Redis
    restart its first call on an old connection fails, and without the retry
    every open line would drop once. Nothing waits on it the way a send does."""
    return redis.asyncio.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=CONNECT_SECONDS,
        retry=redis.asyncio.retry.Retry(NoBackoff(), 1),
    )


# Two clients for the same Redis (D22).
client = new_client(settings.redis_url)

# The async one is made when the app starts and closed when it stops
# (main.py): it only works inside the event loop it was made in.
async_client: redis.asyncio.Redis | None = None


def start() -> None:
    global async_client
    async_client = new_async_client(settings.redis_url)


async def stop() -> None:
    await async_client.aclose()


def _now() -> float:
    """Seconds since 1970, a real clock time: last seen is shown to people, and
    every backend copy must agree on it. Tests swap this to fake the time."""
    return time.time()


def _tabs_key(user_id: uuid.UUID) -> str:
    # A sorted set: each open tab, scored by its "alive until" time.
    return f"presence:{user_id}"


def _last_seen_key(user_id: uuid.UUID) -> str:
    return f"last_seen:{user_id}"


async def tab_alive(user_id: uuid.UUID, tab_id: uuid.UUID) -> bool:
    """This tab is still here (hello or ping): push its "alive until" 60 s
    ahead. Returns True if the person just came online: no tab was alive before."""
    now = _now()
    key = _tabs_key(user_id)
    # One transaction: Redis runs the whole list in one go, with nothing from
    # another tab in between.
    async with async_client.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, "-inf", now)  # wipe tabs whose time has passed
        pipe.zcard(key)  # how many tabs are alive, before this one counts
        pipe.zadd(key, {str(tab_id): now + ALIVE_SECONDS})
        # The whole key's own timer: if every tab goes silent, Redis wipes it.
        pipe.expire(key, ALIVE_SECONDS)
        pipe.set(_last_seen_key(user_id), now)
        _, alive_before, *_ = await pipe.execute()
    return alive_before == 0


async def tab_closed(user_id: uuid.UUID, tab_id: uuid.UUID) -> bool:
    """This tab's line ended. Returns True if no tab is left, so the person is
    offline now. Also True if this tab's time had already run out: the others
    may not know yet."""
    now = _now()
    key = _tabs_key(user_id)
    async with async_client.pipeline(transaction=True) as pipe:
        pipe.zrem(key, str(tab_id))
        pipe.zremrangebyscore(key, "-inf", now)
        pipe.zcard(key)  # tabs still alive
        pipe.set(_last_seen_key(user_id), now)
        _, _, alive_after, _ = await pipe.execute()
    return alive_after == 0


class Status(NamedTuple):
    online: bool
    last_seen: datetime | None


# What the chat list shows when Redis can't say: "last seen recently" in the app (D24).
UNKNOWN = Status(online=False, last_seen=None)


def statuses(user_ids: list[uuid.UUID]) -> dict[uuid.UUID, Status]:
    """Online and last seen for many people, in one trip to Redis (the chat
    list). If Redis is down, every one of them is UNKNOWN."""
    now = _now()
    try:
        # transaction=False: just a batch of reads, sent together.
        with client.pipeline(transaction=False) as pipe:
            for user_id in user_ids:
                # Online = at least one tab whose "alive until" is still ahead.
                # "(" means "above now", not "now or above". A crashed tab
                # never said goodbye, but its time has passed, so it doesn't count.
                pipe.zcount(_tabs_key(user_id), f"({now}", "+inf")
                pipe.get(_last_seen_key(user_id))
            answers = pipe.execute()
    except redis.RedisError:
        log.warning("Redis is down, online status unknown")
        return {user_id: UNKNOWN for user_id in user_ids}

    found = {}
    # The answers come back in pairs, in the same order: (tabs alive, last seen).
    for user_id, alive, seconds in zip(user_ids, answers[0::2], answers[1::2]):
        seen = None if seconds is None else datetime.fromtimestamp(float(seconds), UTC)
        found[user_id] = Status(online=alive > 0, last_seen=seen)
    return found


def last_seen(user_id: uuid.UUID) -> datetime | None:
    """When this person's app last pinged or closed. None if never."""
    seconds = client.get(_last_seen_key(user_id))
    if seconds is None:
        return None
    return datetime.fromtimestamp(float(seconds), UTC)
