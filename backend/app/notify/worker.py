"""The notification worker (D25). Run it in its own terminal:
    python -m app.notify.worker
It reads jobs from notify and notifies people who haven't read their message."""

import json
import logging
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass

import pika
import pika.exceptions
import redis
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties
from sqlalchemy import select

from app.auth.models import User
from app.chats.models import ChatMember
from app.config import settings
from app.db import SessionLocal
from app.messages.models import Message
from app.notify import queues
from app.notify.notifier import LogNotifier, fake_fail
from app.presence import service as presence

log = logging.getLogger(__name__)

# How many jobs RabbitMQ lends the worker at once, before any are acked.
PREFETCH = 10
# Try 1, then one more try per retry box: 4 in all (D25).
MAX_TRIES = 1 + len(queues.RETRIES)
# "Already notified" notes last a day: long past any retry.
NOTIFIED_SECONDS = 24 * 60 * 60
# Reconnect waits 1, 2, 4 ... up to 30 s.
BACKOFF_MAX_SECONDS = 30
# How often the loop wakes up with no jobs, to check whether to stop.
IDLE_SECONDS = 1

redis_client = presence.new_client(settings.redis_url)
notifier = LogNotifier()


class BrokenJob(Exception):
    """Bad JSON or missing fields: no retry can fix it."""


@dataclass
class Job:
    message_id: uuid.UUID
    chat_id: uuid.UUID
    seq: int
    recipient_id: uuid.UUID


def parse(body: bytes) -> Job:
    try:
        data = json.loads(body)
        return Job(
            message_id=uuid.UUID(data["message_id"]),
            chat_id=uuid.UUID(data["chat_id"]),
            seq=int(data["seq"]),
            recipient_id=uuid.UUID(data["recipient_id"]),
        )
    except (ValueError, KeyError, TypeError) as error:
        raise BrokenJob(f"{type(error).__name__}: {error}") from error


def _notified_key(job: Job) -> str:
    return f"notified:{job.message_id}:{job.recipient_id}"


def handle(job: Job, attempt: int) -> str:
    """Do one job. Returns what happened: "sent", or why it was skipped.
    Raises if anything fails (the notifier, PostgreSQL, Redis): try again later."""
    with SessionLocal() as db:
        # The recipient's read bookmark and name. Every door moves read_up_to
        # in PostgreSQL (live line, HTTP door, or their own reply), so this is the truth.
        member = db.execute(
            select(ChatMember.read_up_to, User.name)
            .join(User, User.id == ChatMember.user_id)
            .where(ChatMember.chat_id == job.chat_id, ChatMember.user_id == job.recipient_id)
        ).one_or_none()
        sender_name = db.scalar(
            select(User.name).join(Message, Message.sender_id == User.id).where(Message.id == job.message_id)
        )

    if member is None or sender_name is None:
        return "skip: message or member gone"  # no retry can bring them back (D25)
    if member.read_up_to >= job.seq:
        return "skip: already read"  # they saw it live
    if redis_client.exists(_notified_key(job)):
        return "skip: already notified"  # this job ran before, then came back

    fake_fail(attempt)
    notifier.send(job.recipient_id, member.name, f"New message from {sender_name}")
    try:
        redis_client.set(_notified_key(job), 1, ex=NOTIFIED_SECONDS)
    except redis.RedisError:
        # Already notified, so don't retry: that would notify them again.
        log.warning("Sent, but couldn't note it in Redis")
    return "sent"


def _attempt(properties: BasicProperties) -> int:
    attempt = (properties.headers or {}).get("attempt", 1)
    return attempt if isinstance(attempt, int) and attempt >= 1 else 1


def _retry_or_park(channel: BlockingChannel, body: bytes, label: str, attempt: int, error: str) -> None:
    # The channel has confirms on, so send_job waits for RabbitMQ's "got it".
    # Only then is the original acked: the job is never in no box at all.
    if attempt < MAX_TRIES:
        # Try 1 failed → retry box 1 (10 s), try 2 → box 2 (1 min), try 3 → box 3 (5 min).
        box = queues.RETRIES[attempt - 1]
        queues.send_job(channel, box, body, {"attempt": attempt + 1})
        seconds = settings.notify_retry_ms[attempt - 1] / 1000
        log.warning("%s, try %s: failed (%s), next try in %g s", label, attempt, error, seconds)
    else:
        queues.send_job(channel, queues.FAILED, body, {"attempt": attempt, "last_error": error})
        log.error("%s, try %s: failed (%s), parked in %s", label, attempt, error, queues.FAILED)


def on_job(channel: BlockingChannel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
    """One job from notify: do it, retry it or park it, then ack it, always last."""
    attempt = _attempt(properties)
    try:
        job = parse(body)
    except BrokenJob as error:
        # Straight to the parked jobs: retrying can't fix bad JSON (D25).
        queues.send_job(channel, queues.FAILED, body, {"attempt": attempt, "last_error": f"broken job: {error}"})
        log.error("Broken job parked in %s: %s", queues.FAILED, error)
        channel.basic_ack(method.delivery_tag)
        return

    label = f"#{job.seq} for {str(job.recipient_id)[:8]}"
    try:
        outcome = handle(job, attempt)
    except Exception as error:
        # The notifier, PostgreSQL or Redis failed: maybe fine later (D25).
        _retry_or_park(channel, body, label, attempt, f"{type(error).__name__}: {error}")
    else:
        log.info("%s, try %s: %s", label, attempt, outcome)
    channel.basic_ack(method.delivery_tag)


def open_channel(connection: pika.BlockingConnection) -> BlockingChannel:
    channel = connection.channel()
    channel.confirm_delivery()
    queues.declare(channel)
    channel.basic_qos(prefetch_count=PREFETCH)
    return channel


def consume(channel: BlockingChannel, should_stop: Callable[[], bool]) -> None:
    """Handle jobs from notify until should_stop() says so. Wakes up at least
    every IDLE_SECONDS to ask it."""
    for method, properties, body in channel.consume(queues.NOTIFY, inactivity_timeout=IDLE_SECONDS):
        if method is not None:  # None: no job this time, just the wake-up
            on_job(channel, method, properties, body)
        if should_stop():
            break
    # Jobs lent out but not started go back to notify.
    channel.cancel()


def serve() -> None:
    """Run forever. If RabbitMQ drops, reconnect with backoff (1, 2, 4 ... 30 s)."""
    wait = 1
    while True:
        try:
            connection = queues.connect()
        except pika.exceptions.AMQPConnectionError:
            log.warning("Can't reach RabbitMQ, trying again in %s s", wait)
            time.sleep(wait)
            wait = min(wait * 2, BACKOFF_MAX_SECONDS)
            continue

        wait = 1
        try:
            channel = open_channel(connection)
            log.info("Worker ready: waiting for jobs in %s", queues.NOTIFY)
            consume(channel, should_stop=lambda: False)
        except pika.exceptions.AMQPConnectionError:
            log.warning("Lost RabbitMQ, reconnecting")
        finally:
            # Also on Ctrl+C: closing hands every unacked job back to RabbitMQ,
            # so the one in progress is done again next time, not lost.
            with suppress(Exception):
                connection.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # pika prints a page of tracebacks for every failed connect. Our own
    # one-line warnings already say what happened.
    logging.getLogger("pika").setLevel(logging.CRITICAL)
    try:
        serve()
    except KeyboardInterrupt:
        log.info("Stopped. Unfinished jobs went back to RabbitMQ.")


if __name__ == "__main__":
    main()
