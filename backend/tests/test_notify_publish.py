import json
import logging
import uuid

from app.config import settings
from app.notify import publisher, queues

# Nothing listens here, so every connect fails the way a stopped RabbitMQ does.
DEAD_RABBITMQ = "amqp://parley:x@127.0.0.1:1/parley_test"


def _start_chat(client, me, email) -> str:
    response = client.post("/api/chats/direct", json={"email": email}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _send(client, me, chat_id, body="hi", client_msg_id=None):
    return client.post(
        f"/api/chats/{chat_id}/messages",
        json={"client_msg_id": str(client_msg_id or uuid.uuid4()), "body": body},
        headers=me,
    )


def _my_id(client, me) -> str:
    return client.get("/api/auth/me", headers=me).json()["id"]


def _jobs_in(channel, box) -> list[tuple[dict, dict]]:
    """Take every job out of a box: (body, headers) for each."""
    jobs = []
    while True:
        method, properties, body = channel.basic_get(box, auto_ack=True)
        if method is None:
            return jobs
        jobs.append((json.loads(body), properties.headers))


def test_a_send_puts_one_job_per_other_member_in_wait_with_no_text(client, sign_up, rabbit):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    client_msg_id = uuid.uuid4()

    sent = _send(client, ana, chat_id, "my secret plans", client_msg_id).json()
    # A resend of the same message is not a new message: no second job.
    _send(client, ana, chat_id, "my secret plans", client_msg_id)

    # Taken out before the 1 s timer moves it on to notify.
    [(job, headers)] = _jobs_in(rabbit, queues.WAIT)
    # One job, for Ben only, never for Ana herself.
    assert job == {
        "message_id": sent["id"],
        "chat_id": chat_id,
        "seq": 1,
        "recipient_id": _my_id(client, ben),
    }
    assert headers == {"attempt": 1}
    # Ids and numbers only, never the text (D12).
    assert "secret" not in json.dumps(job)


def test_with_rabbitmq_down_a_send_still_gives_201_and_is_saved(client, sign_up, monkeypatch, caplog):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    monkeypatch.setattr(settings, "rabbitmq_url", DEAD_RABBITMQ)

    with caplog.at_level(logging.WARNING):
        reply = _send(client, ana, chat_id)

    assert reply.status_code == 201
    assert "RabbitMQ is down" in caplog.text
    # Saved in PostgreSQL: only the notification is lost (D25).
    history = client.get(f"/api/chats/{chat_id}/messages", headers=ana).json()
    assert [message["seq"] for message in history["messages"]] == [1]


def test_after_a_failed_connect_the_next_send_skips_without_waiting(client, sign_up, monkeypatch, caplog):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    monkeypatch.setattr(settings, "rabbitmq_url", DEAD_RABBITMQ)
    # Count the tries to reach RabbitMQ. (Counting, not timing: on Linux a
    # refused connect is instant, so both sends would look fast anyway.)
    tries = []
    real_connect = queues.connect

    def counting_connect(url=None):
        tries.append(1)
        return real_connect(url)

    monkeypatch.setattr(queues, "connect", counting_connect)

    with caplog.at_level(logging.WARNING):
        replies = [_send(client, ana, chat_id) for _ in range(2)]

    assert [reply.status_code for reply in replies] == [201, 201]
    # Only the first send tried (and waited); the second skipped (D25).
    assert len(tries) == 1
    # And it was logged once, not once per send.
    assert caplog.text.count("RabbitMQ is down") == 1
    assert publisher._skip_until > 0
