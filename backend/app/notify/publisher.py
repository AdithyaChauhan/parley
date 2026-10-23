import json
import logging
import threading
import time
import uuid
from contextlib import suppress

import pika
import pika.exceptions
from pika.adapters.blocking_connection import BlockingChannel

from app.messages.models import Message
from app.notify import queues

log = logging.getLogger(__name__)

# A send waits at most this long for its turn on the connection (D25).
LOCK_WAIT_SECONDS = 1
# After a failed connect, don't even try for this long (D25), so an outage
# doesn't add 1 s to every send.
SKIP_SECONDS = 10

# One connection for the whole backend copy. pika isn't thread-safe, and sync
# routes run on many threads, so only the thread holding the lock may use it.
_lock = threading.Lock()
_connection: pika.BlockingConnection | None = None
_channel: BlockingChannel | None = None
# Until when to skip publishing, after a failed connect.
_skip_until = 0.0


def _now() -> float:
    """A clock that only goes forward (not the wall clock), for the 10 s skip."""
    return time.monotonic()


def _open() -> None:
    global _connection, _channel
    # Kept at once, so _close() can close it if a step below fails.
    _connection = queues.connect()
    _channel = _connection.channel()
    # Publisher confirms: every publish now waits for RabbitMQ's "got it".
    _channel.confirm_delivery()
    # Every new connection makes sure the boxes exist (D25): the backend may
    # have started while RabbitMQ was down.
    queues.declare(_channel)


def _close() -> None:
    global _connection, _channel
    if _connection is not None:
        with suppress(Exception):  # it may be dead already
            _connection.close()
    _connection = _channel = None


def _send(jobs: list[dict]) -> None:
    for job in jobs:
        queues.send_job(_channel, queues.WAIT, json.dumps(job), {"attempt": 1})


def _publish_locked(jobs: list[dict]) -> None:
    global _skip_until
    # Checked again here: another thread may have just found RabbitMQ down.
    if _now() < _skip_until:
        return

    # An old connection may be stale: RabbitMQ restarted, or it closed one that
    # sat idle. Then it gets one fresh try.
    if _connection is not None:
        try:
            _send(jobs)
            return
        except pika.exceptions.AMQPError:
            _close()

    try:
        _open()
    except pika.exceptions.AMQPConnectionError:
        # Can't reach it at all. Other errors (like a box with a different
        # timer, 406) aren't "down": publish() logs them with the real reason.
        _close()
        _skip_until = _now() + SKIP_SECONDS
        # Logged once per skip, not once per send.
        log.warning("RabbitMQ is down: skipping notifications for %s s", SKIP_SECONDS)
        return

    try:
        _send(jobs)
    except pika.exceptions.AMQPError:
        _close()
        log.exception("Notification jobs lost")


def publish(message: Message, recipient_ids: list[uuid.UUID]) -> None:
    """Drop one job per recipient into notify.wait, after the message is saved
    (D25). Ids and numbers only, never the text (D12). Never raises and never
    waits long: if RabbitMQ is down, the send still succeeds and these
    notifications are lost (accepted, D25)."""
    jobs = [
        {
            "message_id": str(message.id),
            "chat_id": str(message.chat_id),
            "seq": message.seq,
            "recipient_id": str(recipient_id),
        }
        for recipient_id in recipient_ids
    ]
    # Quiet while skipping: the warning was already logged.
    if not jobs or _now() < _skip_until:
        return

    if not _lock.acquire(timeout=LOCK_WAIT_SECONDS):
        log.warning("RabbitMQ connection busy: notification for message %s lost", message.id)
        return
    try:
        _publish_locked(jobs)
    except Exception:
        # Whatever else goes wrong, the send must not fail (D25).
        _close()
        log.exception("Notification jobs lost")
    finally:
        _lock.release()


def reset() -> None:
    """Forget the connection and the skip. For tests, so each one starts fresh."""
    global _skip_until
    with _lock:
        _close()
        _skip_until = 0.0
