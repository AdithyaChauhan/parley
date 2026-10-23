import time
import uuid
from datetime import UTC, datetime

import redis
import redis.asyncio

from app.config import settings

# A tab counts as alive for this long after its last ping. The app pings every
# 25 s (D21), so a living tab always pings again in time, even if one is lost.
ALIVE_SECONDS = 60

# Two clients for the same Redis (D22). decode_responses: answers come back as
# text, not raw bytes.
# The normal one, for normal (def) routes like the chat list.
client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

# The async one, for the live line. Made when the app starts and closed when it
# stops (main.py): it only works inside the event loop it was made in.
async_client: redis.asyncio.Redis | None = None


def start() -> None:
    global async_client
    async_client = redis.asyncio.Redis.from_url(settings.redis_url, decode_responses=True)


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


def is_online(user_id: uuid.UUID) -> bool:
    """At least one of this person's tabs is still alive."""
    key = _tabs_key(user_id)
    # Clear out dead tabs first: a crashed tab never said goodbye.
    client.zremrangebyscore(key, "-inf", _now())
    return client.zcard(key) > 0


def last_seen(user_id: uuid.UUID) -> datetime | None:
    """When this person's app last pinged or closed. None if never."""
    seconds = client.get(_last_seen_key(user_id))
    if seconds is None:
        return None
    return datetime.fromtimestamp(float(seconds), UTC)
