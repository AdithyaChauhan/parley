"""Send every parked job back to the worker (D25), for "the push service was
down for an hour, it's fixed now, send them all". Run:
    python -m app.notify.replay"""

from pika.adapters.blocking_connection import BlockingChannel

from app.notify import queues


def replay(channel: BlockingChannel) -> int:
    """Move every job in notify.failed back to notify, as try 1 again.
    Returns how many it moved."""
    # Only the ones parked right now. A broken job parks itself again at once,
    # and without this count we'd keep moving it round and round.
    waiting = channel.queue_declare(queues.FAILED, passive=True).method.message_count

    moved = 0
    for _ in range(waiting):
        method, _properties, body = channel.basic_get(queues.FAILED)
        if method is None:
            break  # someone else emptied it first
        # A fresh start: try 1, all retries again.
        queues.send_job(channel, queues.NOTIFY, body, {"attempt": 1})
        # Ack the parked copy only after RabbitMQ confirmed the new one.
        channel.basic_ack(method.delivery_tag)
        moved += 1
    return moved


def main() -> None:
    connection = queues.connect()
    try:
        channel = connection.channel()
        channel.confirm_delivery()
        queues.declare(channel)
        moved = replay(channel)
        print(f"Moved {moved} jobs from {queues.FAILED} back to {queues.NOTIFY}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
