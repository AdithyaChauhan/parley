"""Fail fast, and hold no connection during slow work (D34). The real-server tests
are in test_under_load.py."""

import uuid
from contextlib import contextmanager

import anyio.to_thread
import sqlalchemy.exc
from fastapi.routing import APIRoute, iter_route_contexts
from sqlalchemy import text

from app import busy
from app.db import CAPACITY, engine
from app.live import bus
from app.live import routes as live_routes
from app.main import app
from app.notify import publisher
from app.presence import service as presence


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
    ticket = client.post("/api/live/ticket", headers=me).json()["ticket"]
    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"
        yield line


def test_a_send_holds_no_connection_during_its_pushes(client, sign_up, monkeypatch):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    held = {}
    monkeypatch.setattr(bus, "publish", lambda users, event: held.update(redis=engine.pool.checkedout()))
    monkeypatch.setattr(publisher, "publish", lambda message, users: held.update(rabbitmq=engine.pool.checkedout()))

    assert _send(client, ana, chat_id).status_code == 201

    assert held == {"redis": 0, "rabbitmq": 0}


def test_a_read_holds_no_connection_during_its_receipt(client, sign_up, monkeypatch):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    _send(client, ana, chat_id)
    held = {}
    monkeypatch.setattr(bus, "publish", lambda users, event: held.update(redis=engine.pool.checkedout()))

    assert client.post(f"/api/chats/{chat_id}/read", json={"seq": 1}, headers=ben).status_code == 200

    assert held == {"redis": 0}


def test_the_chat_list_holds_no_connection_while_it_asks_redis(client, sign_up, monkeypatch):
    ana = sign_up("Ana")
    sign_up("Ben")
    _start_chat(client, ana, "ben@example.com")
    real_statuses = presence.statuses
    held = {}

    def statuses(user_ids):
        held["redis"] = engine.pool.checkedout()
        return real_statuses(user_ids)

    monkeypatch.setattr(presence, "statuses", statuses)

    assert client.get("/api/chats", headers=ana).status_code == 200

    assert held == {"redis": 0}


def test_no_free_connection_means_503_not_500(client, sign_up, monkeypatch):
    ana = sign_up("Ana")
    monkeypatch.setattr(engine.pool, "_timeout", 0.1)

    # Every connection in use, and no spares beyond them (max_overflow=0).
    held = [engine.connect() for _ in range(CAPACITY)]
    try:
        response = client.get("/api/auth/me", headers=ana)
    finally:
        for connection in held:
            connection.close()

    assert response.status_code == 503
    assert response.json()["detail"] == busy.DETAIL
    assert response.headers["Retry-After"] in {"1", "2", "3"}
    # And right after, it works again.
    assert client.get("/api/auth/me", headers=ana).status_code == 200


def test_threads_and_connections_are_the_same_number(client):
    threads = client.portal.call(lambda: anyio.to_thread.current_default_thread_limiter().total_tokens)

    assert threads == engine.pool.size() == CAPACITY


def test_postgres_ends_a_stuck_transaction_after_a_minute(db):
    assert db.scalar(text("show idle_in_transaction_session_timeout")) == "1min"


def test_a_busy_database_drops_the_event_not_the_line(client, sign_up, monkeypatch):
    ana = sign_up("Ana")

    def no_connection_free(*args):
        raise sqlalchemy.exc.TimeoutError()

    monkeypatch.setattr(live_routes, "_save_bookmark", no_connection_free)

    with _open_line(client, ana) as line:
        line.send_json({"type": "read", "data": {"chat_id": str(uuid.uuid4()), "seq": 1}})
        # The line is still up: the next event gets its answer.
        line.send_json({"type": "ping", "data": {}})
        assert line.receive_json()["type"] == "pong"


def test_every_route_that_does_work_needs_a_slot():
    # Free on purpose: nothing heavy, and they should answer during overload.
    free = {"/metrics", "/api/health", "/api/health/db", "/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}
    # These two check a password, so they take the smaller gate.
    password_routes = {"/api/auth/signup", "/api/auth/login"}
    gates = (busy.REQUEST_SLOT, busy.PASSWORD_SLOT)

    checked = 0
    for context in iter_route_contexts(app.routes):
        if not isinstance(context.original_route, APIRoute) or context.path_format in free:
            continue
        checked += 1
        expected = busy.PASSWORD_SLOT if context.path_format in password_routes else busy.REQUEST_SLOT
        assert [gate for gate in context.dependencies if gate in gates] == [expected], context.path_format

    assert checked > 10
