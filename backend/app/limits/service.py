import logging
import math
import time
import uuid
from typing import NamedTuple

import redis
from fastapi import HTTPException, status

# The Redis clients made in T20 (D22). Used as presence.client, like tickets.py.
from app.presence import service as presence

log = logging.getLogger(__name__)


class Rule(NamedTuple):
    """One limit from D24: at most `limit` requests in any `window_seconds`."""

    name: str  # the middle of the Redis key: limit:<name>:<who>
    limit: int
    window_seconds: int


# Every limit in one place (D24).
SEND = Rule("send", 20, 10)  # per user
LOGIN_EMAIL = Rule("login_email", 5, 15 * 60)  # tries per email, cleared by a good log-in
LOGIN_IP = Rule("login_ip", 30, 15 * 60)  # any log-in, per IP
SIGNUP_IP = Rule("signup_ip", 5, 60 * 60)  # per IP
START_CHAT = Rule("start_chat", 20, 60)  # per user
TICKET = Rule("ticket", 10, 60)  # per user


def key(rule: Rule, who: object) -> str:
    """limit:send:<Ana's id>, limit:login_email:ana@example.com, ..."""
    return f"limit:{rule.name}:{who}"


def hit(key: str, limit: int, window_seconds: int) -> int:
    """Count one more request on this key. Returns 0 if it's allowed, or how
    many seconds to wait until it would be (the sliding window, D24).
    If Redis is down, every request is allowed: better a little spam than no chat."""
    # A real clock time, so every backend copy agrees on it.
    now = time.time()
    # Each request gets its own random name in the set, so two at the same
    # instant are still two entries, not one.
    me = uuid.uuid4().hex
    try:
        # One transaction: Redis runs the whole list in one go, with no other
        # request's steps in between.
        with presence.client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, "-inf", now - window_seconds)  # times that left the window
            pipe.zadd(key, {me: now})
            pipe.zcard(key)  # requests in the window, this one included
            pipe.zrange(key, 0, 0, withscores=True)  # the oldest one: [(name, time)]
            # The key's own timer: once nobody hits it for a whole window,
            # every time in it is too old anyway, so Redis wipes it.
            pipe.expire(key, window_seconds)
            _, _, count, oldest, _ = pipe.execute()

        if count <= limit:
            return 0
        # Over the limit. A transaction can't say "only add if under the limit",
        # so we added first, and now take this one back: a refused request
        # doesn't count. Two at once can't both slip through: each one's count
        # includes the other.
        presence.client.zrem(key, me)
    except redis.RedisError:
        log.warning("Redis is down, letting %s through", key)
        return 0

    # Room opens up when the oldest time leaves the window. At least 1 s,
    # and whole seconds, because that's what Retry-After carries.
    _, oldest_time = oldest[0]
    return max(1, math.ceil(oldest_time + window_seconds - now))


def clear(key: str) -> None:
    """Forget every request on this key (a good log-in clears its email's tries)."""
    try:
        presence.client.delete(key)
    except redis.RedisError:
        log.warning("Redis is down, couldn't clear %s", key)


def enforce(rule: Rule, who: object) -> None:
    """hit() for one of the rules above, for the routes: a refusal becomes
    429 "Too many requests" with Retry-After, the seconds to wait."""
    wait = hit(key(rule, who), rule.limit, rule.window_seconds)
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many requests, slow down",
            headers={"Retry-After": str(wait)},
        )
