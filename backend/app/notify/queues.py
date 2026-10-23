import pika
from pika.adapters.blocking_connection import BlockingChannel

from app.config import settings

# Every box (queue) for notification jobs, in one place (D25).
# The worker reads only this one.
NOTIFY = "notify"
# Every new job waits here first, so a message read live is skipped.
WAIT = "notify.wait"
# Before try 2, 3 and 4. The names say the real waits; tests shrink the timers.
RETRIES = ["notify.retry.10s", "notify.retry.1m", "notify.retry.5m"]
# Parked jobs: they stay here until replay sends them back.
FAILED = "notify.failed"
ALL = [NOTIFY, WAIT, *RETRIES, FAILED]

# Give up fast when RabbitMQ is down: at most 1 s to reach it, 2 s to log in.
CONNECT_SECONDS = 1
SETUP_SECONDS = 2


def connect(url: str | None = None) -> pika.BlockingConnection:
    """A connection to RabbitMQ (the app's own, unless a url is given). One try:
    whoever calls this decides whether to try again."""
    params = pika.URLParameters(url or settings.rabbitmq_url)
    params.connection_attempts = 1
    params.socket_timeout = CONNECT_SECONDS
    params.stack_timeout = SETUP_SECONDS
    return pika.BlockingConnection(params)


def send_job(channel: BlockingChannel, box: str, body: str | bytes, headers: dict) -> None:
    """Put one job in a box. On a channel with confirms on, this waits for
    RabbitMQ's "got it", and raises if it doesn't come."""
    channel.basic_publish(
        exchange="",  # the default exchange delivers by box name
        routing_key=box,
        body=body,
        properties=pika.BasicProperties(
            content_type="application/json",
            # Written to disk, so the job survives a RabbitMQ restart.
            delivery_mode=pika.DeliveryMode.Persistent,
            headers=headers,
        ),
        # If no box takes it, say so instead of dropping it quietly.
        mandatory=True,
    )


def _timer_box(channel: BlockingChannel, name: str, ms: int) -> None:
    channel.queue_declare(
        name,
        durable=True,
        arguments={
            # Every job in this box waits the same time (the box's timer, not
            # the job's), so the one at the front is always the next one due.
            "x-message-ttl": ms,
            # When the time is up, the job is "dead-lettered": sent on through
            # the default exchange "" (it delivers by box name) into notify.
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": NOTIFY,
        },
    )


def declare(channel: BlockingChannel) -> None:
    """Make every box if it isn't there yet. Making one that's already there
    with the same settings does nothing, so the backend and the worker both
    call this whenever they connect. A different timer is refused (error 406):
    delete that box first (D25).
    durable: the box survives a RabbitMQ restart (the jobs survive too, if they
    are sent as persistent)."""
    channel.queue_declare(NOTIFY, durable=True)
    channel.queue_declare(FAILED, durable=True)
    _timer_box(channel, WAIT, settings.notify_wait_ms)
    for name, ms in zip(RETRIES, settings.notify_retry_ms, strict=True):
        _timer_box(channel, name, ms)
