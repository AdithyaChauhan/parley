import logging
import time
import uuid

import pytest
from prometheus_client import REGISTRY

from app.config import settings
from app.notify import notifier, queues, replay, worker
from app.notify.notifier import LogNotifier
from app.presence import service as presence


@pytest.fixture(autouse=True)
def quick_worker(monkeypatch, caplog):
    # Wake up often, so a test stops soon after what it waits for happens.
    monkeypatch.setattr(worker, "IDLE_SECONDS", 0.1)
    caplog.set_level(logging.INFO)


def _start_chat(client, me, email) -> str:
    response = client.post("/api/chats/direct", json={"email": email}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _send(client, me, chat_id):
    reply = client.post(
        f"/api/chats/{chat_id}/messages",
        json={"client_msg_id": str(uuid.uuid4()), "body": "hi"},
        headers=me,
    )
    assert reply.status_code == 201
    return reply.json()


def _ana_sends_ben(client, sign_up):
    """Ana sends Ben #1. Returns Ben's login header and the chat id."""
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    _send(client, ana, chat_id)
    return ben, chat_id


def _run_worker(channel, until, seconds=10):
    """Run the worker's loop until until() is true, or fail after a while."""
    deadline = time.monotonic() + seconds
    worker.consume(channel, should_stop=lambda: until() or time.monotonic() > deadline)
    assert until(), "the worker never got there"


def _count(channel, box) -> int:
    return channel.queue_declare(box, passive=True).method.message_count


def _logged(caplog, text):
    return lambda: text in caplog.text


def _tries(outcome) -> float:
    """The worker's notify_jobs_total for one outcome, as /metrics shows it (D32)."""
    return REGISTRY.get_sample_value("notify_jobs_total", {"outcome": outcome})


def test_sends_when_unread_and_notes_it_in_redis(client, sign_up, rabbit, caplog):
    _ana_sends_ben(client, sign_up)

    # The job waits 1 s in notify.wait, falls into notify, and the worker takes it.
    _run_worker(rabbit, _logged(caplog, "try 1: sent"))

    assert "notify Ben: New message from Ana" in caplog.text
    [key] = presence.client.keys("notified:*")
    # The "already notified" note lasts about a day (D25).
    assert 0 < presence.client.ttl(key) <= notifier.NOTIFIED_SECONDS


def test_skips_when_already_read(client, sign_up, rabbit, caplog):
    ben, chat_id = _ana_sends_ben(client, sign_up)
    # Ben reads it within the wait (through the HTTP door, D20).
    client.post(f"/api/chats/{chat_id}/read", json={"seq": 1}, headers=ben)
    skipped, sent = _tries("skip: already read"), _tries("sent")

    _run_worker(rabbit, _logged(caplog, "try 1: skip: already read"))

    assert "notify Ben" not in caplog.text
    # The skip moves its own counter, and only that one.
    assert _tries("skip: already read") == skipped + 1
    assert _tries("sent") == sent


def test_a_job_that_runs_twice_notifies_once(client, sign_up, rabbit, caplog):
    _ana_sends_ben(client, sign_up)
    # Take the job before its timer ends and put two copies in notify: what
    # "at least once" can do after a crash between the send and the ack.
    method, _properties, body = rabbit.basic_get(queues.WAIT, auto_ack=True)
    assert method is not None
    for _ in range(2):
        queues.send_job(rabbit, queues.NOTIFY, body, {"attempt": 1})

    _run_worker(rabbit, _logged(caplog, "skip: already notified"))

    assert caplog.text.count("notify Ben: New message from Ana") == 1


def test_with_two_fake_fails_it_is_sent_on_try_3(client, sign_up, rabbit, caplog, monkeypatch):
    monkeypatch.setattr(settings, "notify_fake_fail_times", 2)
    _ana_sends_ben(client, sign_up)

    _run_worker(rabbit, _logged(caplog, "try 3: sent"))

    assert "try 1: failed (NotifyFailed: fake fail (1 of 2)), next try in 0.1 s" in caplog.text
    assert "try 2: failed (NotifyFailed: fake fail (2 of 2)), next try in 0.2 s" in caplog.text
    assert caplog.text.count("notify Ben:") == 1


def test_with_ten_fake_fails_it_is_parked_after_try_4(client, sign_up, rabbit, caplog, monkeypatch):
    monkeypatch.setattr(settings, "notify_fake_fail_times", 10)
    _ana_sends_ben(client, sign_up)
    failed, parked = _tries("failed"), _tries("parked")

    _run_worker(rabbit, lambda: _count(rabbit, queues.FAILED) == 1)

    # Every try ends one way: 3 retries booked, then parked (D32).
    assert _tries("failed") == failed + 3
    assert _tries("parked") == parked + 1
    assert "try 4: failed (NotifyFailed: fake fail (4 of 10)), parked in notify.failed" in caplog.text
    _method, properties, _body = rabbit.basic_get(queues.FAILED, auto_ack=True)
    assert properties.headers == {"attempt": 4, "last_error": "NotifyFailed: fake fail (4 of 10)"}
    assert "notify Ben" not in caplog.text


@pytest.mark.parametrize("body", [b"not json", b'{"message_id": "abc"}'])
def test_a_broken_job_is_parked_at_once(rabbit, caplog, body):
    queues.send_job(rabbit, queues.NOTIFY, body, {"attempt": 1})

    _run_worker(rabbit, lambda: _count(rabbit, queues.FAILED) == 1)

    # No retries: straight from try 1 to the parked jobs.
    assert "next try" not in caplog.text
    _method, properties, parked = rabbit.basic_get(queues.FAILED, auto_ack=True)
    assert parked == body
    assert properties.headers["attempt"] == 1
    assert properties.headers["last_error"].startswith("broken job:")


def test_replay_moves_parked_jobs_back_and_they_are_sent(client, sign_up, rabbit, caplog, monkeypatch):
    monkeypatch.setattr(settings, "notify_fake_fail_times", 10)
    _ana_sends_ben(client, sign_up)
    _run_worker(rabbit, lambda: _count(rabbit, queues.FAILED) == 1)

    # The push service is fixed: send them all again.
    monkeypatch.setattr(settings, "notify_fake_fail_times", 0)
    assert replay.replay(rabbit) == 1
    assert _count(rabbit, queues.FAILED) == 0

    # Back as try 1, and sent.
    _run_worker(rabbit, _logged(caplog, "try 1: sent"))
    assert "notify Ben: New message from Ana" in caplog.text


def test_a_job_not_acked_is_handed_out_again(client, sign_up, caplog, monkeypatch):
    _ana_sends_ben(client, sign_up)

    # The first worker stops mid-job (Ctrl+C) inside the notifier, before its ack.
    class StoppedMidJob:
        def send(self, *_args):
            raise KeyboardInterrupt

    monkeypatch.setattr(worker, "notifier", StoppedMidJob())
    first = queues.connect()
    with pytest.raises(KeyboardInterrupt):
        _run_worker(worker.open_channel(first), lambda: False)
    # Closing the connection hands the unacked job back to RabbitMQ.
    first.close()
    assert "sent" not in caplog.text

    # A new worker gets the same job again, and this time sends it.
    monkeypatch.setattr(worker, "notifier", LogNotifier(worker.redis_client))
    second = queues.connect()
    try:
        _run_worker(worker.open_channel(second), _logged(caplog, "try 1: sent"))
    finally:
        second.close()
    assert "notify Ben: New message from Ana" in caplog.text
