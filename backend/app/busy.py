"""Saying "busy, try again" instead of freezing (D34). A request that can't start
soon gets a quick 503 with Retry-After. Without this it would wait in a line with
no end, long after its client gave up."""

import random

import anyio
from fastapi import Depends, HTTPException, status

from app.db import CAPACITY

DETAIL = "Busy, try again"

# How long a request waits for a slot before it's told "busy". Well below
# Nginx's 60 s, and short enough that a person is still looking at the screen.
REQUEST_WAIT_SECONDS = 3

# Password checks at once on this copy. Each one uses 64 MB (argon2), and the
# server has about 1 GB free: 2 copies x 3 x 64 MB = 384 MB at worst, which leaves
# room. Above ~8 logins/s with no cap, the laptop swapped and collapsed (T31).
PASSWORD_CHECKS = 3
PASSWORD_WAIT_SECONDS = 2


def retry_after() -> dict[str, str]:
    """1 to 3 s at random, so everyone refused at the same moment doesn't come
    back at the same moment."""
    return {"Retry-After": str(random.randint(1, 3))}


def _gate(slots: int, wait_seconds: float):
    """A FastAPI dependency: at most `slots` requests inside at once. The others
    wait in line, first come first served, for up to wait_seconds, then get 503.
    async, so waiting here costs no thread and no database connection."""
    line = anyio.Semaphore(slots)

    async def enter():
        try:
            with anyio.fail_after(wait_seconds):
                await line.acquire()
        except TimeoutError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, DETAIL, headers=retry_after()) from None
        try:
            yield
        finally:
            line.release()

    return enter


# scope="function": the slot goes back as soon as the answer is ready, not after
# a slow client has finished reading it.
# Every route that does real work takes one of these (test_busy.py checks it).
REQUEST_SLOT = Depends(_gate(CAPACITY, REQUEST_WAIT_SECONDS), scope="function")
PASSWORD_SLOT = Depends(_gate(PASSWORD_CHECKS, PASSWORD_WAIT_SECONDS), scope="function")
