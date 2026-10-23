import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from app.limits import service as limits
from app.presence import service as presence


def _my_id(client, me) -> str:
    return client.get("/api/auth/me", headers=me).json()["id"]


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


def _log_in(client, email, password) -> int:
    return client.post("/api/auth/login", json={"email": email, "password": password}).status_code


def test_the_21st_send_in_10_seconds_gets_429_then_works_after_the_window(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    assert [_send(client, ana, chat_id).status_code for _ in range(20)] == [201] * 20

    refused = _send(client, ana, chat_id)
    assert refused.status_code == 429
    assert 1 <= int(refused.headers["Retry-After"]) <= 10

    # Redis keeps the 10 s window, and its clock can't be faked. So shorten
    # the key's timer to 1 millisecond and let Redis expire it, as for tickets (T21).
    presence.client.pexpire(limits.key(limits.SEND, _my_id(client, ana)), 1)
    time.sleep(0.01)

    again = _send(client, ana, chat_id)
    assert again.status_code == 201
    # The refused send was never saved: this one is #21.
    assert again.json()["seq"] == 21


def test_the_6th_try_locks_the_email_even_with_the_right_password_but_not_others(client, sign_up):
    sign_up("Ana")
    sign_up("Ben")
    assert [_log_in(client, "ana@example.com", "wrong-password") for _ in range(5)] == [401] * 5

    locked = client.post("/api/auth/login", json={"email": "ana@example.com", "password": "wrong-password"})
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0
    # Locked means locked: the right password waits too.
    assert _log_in(client, "ana@example.com", "secret123") == 429
    # Only Ana's email is locked.
    assert _log_in(client, "ben@example.com", "secret123") == 200


def test_a_good_log_in_clears_the_count(client, sign_up):
    sign_up("Ana")
    assert [_log_in(client, "ana@example.com", "wrong-password") for _ in range(4)] == [401] * 4
    assert _log_in(client, "ana@example.com", "secret123") == 200

    # Counting starts again from 0: five more wrong tries before the lock.
    assert [_log_in(client, "ana@example.com", "wrong-password") for _ in range(5)] == [401] * 5
    assert _log_in(client, "ana@example.com", "wrong-password") == 429


def test_sign_up_is_limited_per_ip(client):
    replies = [
        client.post(
            "/api/auth/signup",
            json={"name": f"User {n}", "email": f"user{n}@example.com", "password": "secret123"},
        )
        for n in range(6)
    ]
    # Every test request comes from the same address, like your two windows in dev.
    assert [reply.status_code for reply in replies] == [201] * 5 + [429]
    assert int(replies[-1].headers["Retry-After"]) > 0


def test_requests_at_the_same_moment_never_get_past_the_limit(client):
    # 50 requests at once against a limit of 20: each one's count includes
    # the others, so exactly 20 get through.
    with ThreadPoolExecutor(max_workers=50) as pool:
        waits = list(pool.map(lambda _: limits.hit("limit:test:ana", 20, 10), range(50)))

    assert waits.count(0) == 20
    # The 30 refused ones took themselves back out.
    assert presence.client.zcard("limit:test:ana") == 20
