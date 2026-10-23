import time
import uuid

import pytest
from fastapi import WebSocketDisconnect

from app.live import manager
from app.presence import service as presence


def _ticket(client, me) -> str:
    response = client.post("/api/live/ticket", headers=me)
    assert response.status_code == 200
    return response.json()["ticket"]


def _my_id(client, me) -> str:
    return client.get("/api/auth/me", headers=me).json()["id"]


def _hang_up_code(client, ticket) -> int:
    """Open the line with this ticket and return the code the server hangs up with.
    The server must pick up first, or the browser never sees the code."""
    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        with pytest.raises(WebSocketDisconnect) as closed:
            line.receive_json()
    return closed.value.code


def test_ticket_route_needs_a_login(client, sign_up):
    assert client.post("/api/live/ticket").status_code == 401

    reply = client.post("/api/live/ticket", headers=sign_up("Ana"))
    assert reply.status_code == 200
    assert reply.json()["expires_in"] == 30


def test_a_ticket_works_once(client, sign_up):
    ticket = _ticket(client, sign_up("Ana"))

    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"

    # Someone copies the address from a log and tries it again.
    assert _hang_up_code(client, ticket) == 4401
    assert _hang_up_code(client, "made-up") == 4401


def test_an_expired_ticket_is_refused(client, sign_up):
    ticket = _ticket(client, sign_up("Ana"))

    # Redis keeps the 30 s timer, and its clock can't be faked. So shorten
    # the timer to 1 millisecond instead of waiting, and let Redis expire it.
    presence.client.pexpire(f"ticket:{ticket}", 1)
    time.sleep(0.01)

    assert _hang_up_code(client, ticket) == 4401


def test_a_ticket_lives_in_redis_for_30_seconds_and_is_gone_once_used(client, sign_up):
    ticket = _ticket(client, sign_up("Ana"))
    key = f"ticket:{ticket}"

    # In Redis, so any backend copy can redeem it (D23), with its own timer.
    assert 0 < presence.client.ttl(key) <= 30

    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"

    # GETDEL took it out, so a second redeem, on any copy, finds nothing.
    assert presence.client.exists(key) == 0


def test_a_good_ticket_gets_hello_with_my_id(client, sign_up):
    ana = sign_up("Ana")
    ana_id = _my_id(client, ana)

    with client.websocket_connect(f"/api/live?ticket={_ticket(client, ana)}") as line:
        assert line.receive_json() == {"type": "hello", "data": {"user_id": ana_id}}


def test_ping_gets_pong(client, sign_up):
    ana = sign_up("Ana")

    with client.websocket_connect(f"/api/live?ticket={_ticket(client, ana)}") as line:
        line.receive_json()  # hello
        line.send_json({"type": "ping"})  # no data: counts as {} (D21)
        assert line.receive_json() == {"type": "pong", "data": {}}
        line.send_json({"type": "ping", "data": {}})  # the shape the app sends
        assert line.receive_json() == {"type": "pong", "data": {}}


def test_two_tabs_are_both_on_the_switchboard(client, sign_up):
    ana = sign_up("Ana")
    ana_id = uuid.UUID(_my_id(client, ana))

    with client.websocket_connect(f"/api/live?ticket={_ticket(client, ana)}") as tab_1:
        tab_1.receive_json()  # hello: by now the line is on the switchboard
        with client.websocket_connect(f"/api/live?ticket={_ticket(client, ana)}") as tab_2:
            tab_2.receive_json()
            assert len(manager.lines[ana_id]) == 2

        # Ana closed tab 2. Tab 1 is still open.
        assert len(manager.lines[ana_id]) == 1

    # Both tabs closed: Ana is off the switchboard.
    assert ana_id not in manager.lines
