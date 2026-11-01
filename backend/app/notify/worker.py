"""The notification worker (D25). Run it in its own terminal:
    python -m app.notify.worker
It reads jobs from notify and notifies people who haven't read their message."""

import json
import logging
import signal
import time
import uuid
from collections.abc import Callable
from contextlib import suppress

import pika
import pika.exceptions
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties
from prometheus_client import Counter, disable_created_metrics, start_http_server
from sqlalchemy import select

from app.auth.models import User
from app.chats.models import ChatMember
from app.config import settings
from app.db import SessionLocal
from app.messages.models import Message
from app.notify import queues
from app.notify.notifier import fake_fail, make_notifier
from app.notify.queues import Job
from app.presence import service as presence

log = logging.getLogger(__name__)

# How many jobs RabbitMQ lends the worker at once, before any are acked.
PREFETCH = 10
# Try 1, then one more try per retry box: 4 in all (D25).
MAX_TRIES = 1 + len(queues.RETRIES)
# Reconnect waits 1, 2, 4 ... up to 30 s.
BACKOFF_MAX_SECONDS = 30
# How often the loop wakes up with no jobs, to check whether to stop.
IDLE_SECONDS = 1
# The worker's own /metrics page, for Prometheus (D32). Only reachable inside
# Parley's network, like the backend's port 8000.
METRICS_PORT = 9100

# Without this, every counter also shows a second "_created" line (as in app/metrics.py).
disable_created_metrics()
# One count per try, by how it ended (D32). Every try ends exactly one way, so
# the panel adds up to "tries handled". "failed" is also the retry count.
JOBS = Counter("notify_jobs_total", "Notification job tries, by outcome", ["outcome"])
OUTCOMES = [
    "sent",
    "skip: already read",
    "skip: message or member gone",
    "skip: no devices",
    "skip: already notified",
    "failed",  # this try failed, and a retry was booked
    "parked",  # gave up after try 4, or a broken job: it's in notify.failed
]
# Each outcome shows 0 from the start, so the first one of each isn't hidden
# (Prometheus counts "how many lately" from the change between two visits).
for _outcome in OUTCOMES:
    JOBS.labels(_outcome)

redis_client = presence.new_client(settings.redis_url)
# Log line or real browser push, picked by the setting NOTIFIER (D26).
# With "webpush" and no VAPID keys, this refuses to start.
notifier = make_notifier(redis_client)


class BrokenJob(Exception):
    """Bad JSON or missing fields: no retry can fix it."""


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


def handle(job: Job, attempt: int) -> str:
    """Do one job. Returns what happened: "sent", or why it was skipped.
    Raises if anything fails (the notifier, PostgreSQL, Redis): try again later.
    The "already notified" notes belong to the notifier now (D25)."""
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

    fake_fail(attempt)
    # "sent", "skip: no devices" or "skip: already notified" (D25).
    return notifier.send(job, member.name, f"New message from {sender_name}")


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
        JOBS.labels("failed").inc()
        seconds = settings.notify_retry_ms[attempt - 1] / 1000
        log.warning("%s, try %s: failed (%s), next try in %g s", label, attempt, error, seconds)
    else:
        queues.send_job(channel, queues.FAILED, body, {"attempt": attempt, "last_error": error})
        JOBS.labels("parked").inc()
        log.error("%s, try %s: failed (%s), parked in %s", label, attempt, error, queues.FAILED)


def on_job(channel: BlockingChannel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
    """One job from notify: do it, retry it or park it, then ack it, always last."""
    attempt = _attempt(properties)
    try:
        job = parse(body)
    except BrokenJob as error:
        # Straight to the parked jobs: retrying can't fix bad JSON (D25).
        queues.send_job(channel, queues.FAILED, body, {"attempt": attempt, "last_error": f"broken job: {error}"})
        JOBS.labels("parked").inc()
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
        JOBS.labels(outcome).inc()
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
            log.info("Worker ready (%s): waiting for jobs in %s", settings.notifier, queues.NOTIFY)
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
    # `docker stop` sends SIGTERM, not Ctrl+C. In a container the worker is
    # PID 1, which ignores SIGTERM unless it asks for it. Turn it into Ctrl+C,
    # so it takes the same clean path below (D27).
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    # The /metrics page runs in a small background thread, beside the job loop.
    start_http_server(METRICS_PORT)
    try:
        serve()
    except KeyboardInterrupt:
        log.info("Stopped. Unfinished jobs went back to RabbitMQ.")


if __name__ == "__main__":
    main()
