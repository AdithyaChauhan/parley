"""The freeze from the load test (T31, D34), on a real server with real sockets.
TestClient runs one request at a time and can't hang up, so it can't show this.

What froze a copy: a request held a database connection while it waited for a
thread, and the threads held on while they waited for a connection. So 15 requests
and all 40 threads waited for each other until a 30 s timeout, and clients that
hung up left their requests in the line."""

import asyncio
import json
import socket
import threading
import time
import uuid
from collections import Counter
from contextlib import contextmanager

import httpx2
import pytest
import uvicorn
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db import engine
from app.main import app

# Looks at PostgreSQL from outside the app's pool, so looking doesn't use up one
# of the connections being counted. conftest points settings at the test database.
outside = create_engine(settings.database_url, poolclass=NullPool)


def _stuck_sessions() -> int:
    """Sessions holding a connection in an open transaction and doing nothing."""
    with outside.connect() as connection:
        return connection.scalar(
            text(
                "select count(*) from pg_stat_activity where datname = current_database()"
                " and state = 'idle in transaction' and pid <> pg_backend_pid()"
            )
        )


def _all_connections_back(seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if engine.pool.checkedout() == 0 and _stuck_sessions() == 0:
            return True
        time.sleep(0.1)
    return False


@pytest.fixture
def server(db):
    """The real app on a real port. Gives its address."""
    with socket.socket() as spare:
        spare.bind(("127.0.0.1", 0))
        port = spare.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="critical", timeout_graceful_shutdown=1)
    running = uvicorn.Server(config)
    thread = threading.Thread(target=running.run, daemon=True)
    thread.start()
    while not running.started:
        time.sleep(0.01)

    yield f"http://127.0.0.1:{port}"

    running.should_exit = True
    thread.join(timeout=10)
    # If a test failed with sessions stuck, the db fixture's TRUNCATE would wait
    # on them forever.
    with outside.connect() as connection:
        connection.execute(
            text(
                "select pg_terminate_backend(pid) from pg_stat_activity"
                " where datname = current_database() and pid <> pg_backend_pid()"
            )
        )
    engine.dispose()


def _sign_up(server, name) -> dict[str, str]:
    reply = httpx2.post(
        f"{server}/api/auth/signup",
        json={"name": name, "email": f"{name.lower()}@example.com", "password": "secret123"},
    )
    assert reply.status_code == 201
    return {"Authorization": f"Bearer {reply.json()['access_token']}"}


def _start_chat(server, me, email) -> str:
    return httpx2.post(f"{server}/api/chats/direct", json={"email": email}, headers=me).json()["id"]


@contextmanager
def _holding_chat_row(chat_id):
    """Someone holds the chat's row, so sends to it can't finish until this ends."""
    with outside.begin() as connection:
        connection.execute(text("select 1 from chats where id = :id for update"), {"id": chat_id})
        yield


def _land_together(server, method, path, headers, bodies) -> list[socket.socket]:
    """One request per body, all landing at the same moment: every socket
    connects first, and only then do they all send."""
    host, port = server.removeprefix("http://").split(":")
    sockets = [socket.create_connection((host, int(port))) for _ in bodies]
    extra = "".join(f"{name}: {value}\r\n" for name, value in headers.items())
    requests = []
    for body in bodies:
        data = json.dumps(body).encode() if body is not None else b""
        head = f"{method} {path} HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: {len(data)}\r\n{extra}\r\n"
        requests.append(head.encode() + data)
    for one, request in zip(sockets, requests):
        one.sendall(request)
    return sockets


def _read_reply(one: socket.socket, deadline: float) -> tuple[str, dict[str, str]] | None:
    """The status and headers of the reply on this socket. None if none came in time."""
    one.settimeout(max(0.01, deadline - time.monotonic()))
    try:
        head = one.recv(4096).decode(errors="replace").split("\r\n\r\n")[0].split("\r\n")
    except OSError:
        return None
    pairs = (line.split(": ", 1) for line in head[1:] if ": " in line)
    return head[0].split(" ")[1], {name.lower(): value for name, value in pairs}


def _status(one: socket.socket, deadline: float) -> str:
    reply = _read_reply(one, deadline)
    one.close()
    return reply[0] if reply else "no answer"


def test_abandoned_requests_leave_no_connection_behind(server):
    ana = _sign_up(server, "Ana")
    _sign_up(server, "Ben")
    _start_chat(server, ana, "ben@example.com")

    sockets = _land_together(server, "GET", "/api/chats", ana, [None] * 150)
    time.sleep(1)
    # Everyone gives up mid-flight, like Nginx or a client after a timeout.
    for one in sockets:
        one.close()

    # Well before the old 30 s pool timeout.
    assert _all_connections_back(seconds=10)
    # And the copy isn't frozen: /api/health needs a free thread.
    assert httpx2.get(f"{server}/api/health", timeout=2).status_code == 200


def test_a_burst_gets_quick_answers(server):
    ana = _sign_up(server, "Ana")
    _sign_up(server, "Ben")
    _start_chat(server, ana, "ben@example.com")

    sockets = _land_together(server, "GET", "/api/chats", ana, [None] * 150)
    deadline = time.monotonic() + 8
    answers = Counter(_status(one, deadline) for one in sockets)

    # Everyone hears back within seconds: the chat list, or "busy". Nothing hangs.
    assert set(answers) <= {"200", "503"}, answers
    assert _all_connections_back(seconds=5)


def test_a_stuck_database_means_quick_503s_and_then_recovery(server):
    ana = _sign_up(server, "Ana")
    _sign_up(server, "Ben")
    chat_id = _start_chat(server, ana, "ben@example.com")

    # The slots stay full: the sends that get one can't finish.
    with _holding_chat_row(chat_id):
        bodies = [{"client_msg_id": str(uuid.uuid4()), "body": "hi"} for _ in range(30)]
        sockets = _land_together(server, "POST", f"/api/chats/{chat_id}/messages", ana, bodies)

        # Whoever didn't get a slot hears "busy" well before Nginx's 60 s, and is
        # told when to come back.
        deadline = time.monotonic() + 6
        replies = {one: _read_reply(one, deadline) for one in sockets}

    refused = [reply for reply in replies.values() if reply]
    still_waiting = [one for one, reply in replies.items() if reply is None]
    assert refused, "nobody heard back while the database was stuck"
    assert still_waiting, "nobody got a slot"
    assert {status for status, _ in refused} == {"503"}
    assert all(headers["retry-after"] in {"1", "2", "3"} for _, headers in refused)

    # The row is free now: the ones with a slot finish, and everything goes back.
    deadline = time.monotonic() + 5
    assert {_status(one, deadline) for one in still_waiting} == {"201"}
    assert _all_connections_back(seconds=5)


def test_a_cancelled_request_gives_its_connection_and_slot_back(server):
    ana = _sign_up(server, "Ana")
    _sign_up(server, "Ben")
    chat_id = _start_chat(server, ana, "ben@example.com")
    path = f"/api/chats/{chat_id}/messages"

    async def one_send():
        # The server's own view of a request, so its task can really be cancelled.
        body = json.dumps({"client_msg_id": str(uuid.uuid4()), "body": "hi"}).encode()
        delivered = False

        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            await asyncio.sleep(3600)

        async def send(message):
            pass

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [
                (b"content-type", b"application/json"),
                (b"authorization", ana["Authorization"].encode()),
                (b"content-length", str(len(body)).encode()),
            ],
            "client": ("127.0.0.1", 1),
            "server": ("127.0.0.1", 80),
            "state": {},
        }
        await app(scope, receive, send)

    async def cancel_them_mid_flight():
        with _holding_chat_row(chat_id):
            tasks = [asyncio.create_task(one_send()) for _ in range(20)]
            await asyncio.sleep(1)
            for task in tasks:
                task.cancel()
        # A thread that's already running can't be stopped: it finishes first.
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(cancel_them_mid_flight())

    assert _all_connections_back(seconds=5)
    # Lost slots would turn this into "busy".
    assert httpx2.get(f"{server}/api/chats", headers=ana, timeout=2).status_code == 200


def test_at_most_three_password_checks_at_once(server, monkeypatch):
    now_checking = 0
    most = 0
    count = threading.Lock()

    def slow_check(password, password_hash):
        nonlocal now_checking, most
        with count:
            now_checking += 1
            most = max(most, now_checking)
        time.sleep(0.2)
        with count:
            now_checking -= 1
        return False

    monkeypatch.setattr("app.auth.routes.verify_password", slow_check)

    # A different email each: 5 tries on one email would be refused (D24).
    bodies = [{"email": f"person{n}@example.com", "password": "wrong-password"} for n in range(12)]
    sockets = _land_together(server, "POST", "/api/auth/login", {}, bodies)
    deadline = time.monotonic() + 6
    answers = Counter(_status(one, deadline) for one in sockets)

    assert answers == {"401": 12}
    assert most == 3


def test_logins_past_the_cap_get_a_quick_503(server, monkeypatch):
    def very_slow_check(password, password_hash):
        time.sleep(1.5)
        return False

    monkeypatch.setattr("app.auth.routes.verify_password", very_slow_check)

    # Three at once, 1.5 s each: the last three can't start within their 2 s wait.
    bodies = [{"email": f"person{n}@example.com", "password": "wrong-password"} for n in range(9)]
    sockets = _land_together(server, "POST", "/api/auth/login", {}, bodies)
    deadline = time.monotonic() + 8
    answers = [_read_reply(one, deadline) or ("no answer", {}) for one in sockets]

    statuses = Counter(status for status, _ in answers)
    assert statuses["401"] >= 3
    assert statuses["503"] >= 3
    assert statuses["401"] + statuses["503"] == 9, statuses
    assert all(headers["retry-after"] in {"1", "2", "3"} for status, headers in answers if status == "503")
