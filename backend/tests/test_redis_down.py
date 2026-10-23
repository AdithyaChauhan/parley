import logging
import uuid
from contextlib import contextmanager

import pytest
from fastapi import WebSocketDisconnect

from app.limits import service as limits
from app.presence import service as presence

# Nothing listens here, so every call fails the way a stopped Redis does.
DEAD_REDIS = "redis://127.0.0.1:1/15"


@pytest.fixture
def stop_redis(client, monkeypatch):
    """Call it to "stop" Redis for the normal routes: their client now points
    at the dead address, with the same give-up-fast settings (D24). Put back
    after the test, before the Redis wipe. On Windows each failed call takes
    about 2 s, so these tests are slower there; on Linux (CI) it's instant."""

    def _stop():
        monkeypatch.setattr(presence, "client", presence.new_client(DEAD_REDIS))

    return _stop


def _start_chat(client, me, email) -> str:
    response = client.post("/api/chats/direct", json={"email": email}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _send(client, me, chat_id):
    return client.post(
        f"/api/chats/{chat_id}/messages",
        json={"client_msg_id": str(uuid.uuid4()), "body": "hi"},
        headers=me,
    )


@contextmanager
def _open_line(client, me):
    """One open tab: get a ticket, open the line, read the hello."""
    ticket = client.post("/api/live/ticket", headers=me).json()["ticket"]
    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"
        yield line


def test_sends_are_still_saved_and_limits_let_them_through(client, sign_up, stop_redis, monkeypatch, caplog):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    # A limit of 1: with Redis up, the second send would get 429.
    monkeypatch.setattr(limits, "SEND", limits.Rule("send", 1, 10))
    stop_redis()

    with caplog.at_level(logging.WARNING):
        replies = [_send(client, ana, chat_id) for _ in range(2)]

    assert [reply.status_code for reply in replies] == [201, 201]
    assert "Redis is down, letting limit:send:" in caplog.text
    # Saved in PostgreSQL, the truth (D24): history needs no Redis.
    history = client.get(f"/api/chats/{chat_id}/messages", headers=ana).json()
    assert [message["seq"] for message in history["messages"]] == [2, 1]


def test_the_chat_list_still_loads_with_online_unknown(client, sign_up, stop_redis):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    _start_chat(client, ana, "ben@example.com")

    with _open_line(client, ana):
        assert client.get("/api/chats", headers=ben).json()[0]["online"] is True
        stop_redis()

        reply = client.get("/api/chats", headers=ben)
        assert reply.status_code == 200
        row = reply.json()[0]
        # Unknown: the app shows "last seen recently".
        assert row["online"] is False
        assert row["last_seen"] is None


def test_a_ticket_gets_503(client, sign_up, stop_redis):
    ana = sign_up("Ana")
    stop_redis()

    reply = client.post("/api/live/ticket", headers=ana)
    assert reply.status_code == 503
    assert reply.json()["detail"] == "Live updates unavailable"


def test_an_open_line_closes_cleanly_when_redis_goes_down(client, sign_up, monkeypatch):
    ana = sign_up("Ana")
    with _open_line(client, ana) as line:
        # The live line's own client goes dead too, so the next ping can't
        # mark the tab alive.
        monkeypatch.setattr(presence, "async_client", presence.new_async_client(DEAD_REDIS))
        line.send_json({"type": "ping"})
        assert line.receive_json()["type"] == "pong"  # pong comes first

        with pytest.raises(WebSocketDisconnect) as closed:
            line.receive_json()
    # 1011: "the server hit a problem". The app reconnects with its backoff.
    assert closed.value.code == 1011
