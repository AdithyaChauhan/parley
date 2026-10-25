from sqlalchemy import select

from app.auth.models import User
from app.config import settings
from app.db import SessionLocal
from app.push.models import PushSubscription

EDGE = "https://fcm.googleapis.com/fcm/send/ben-edge"


def _subscribe(client, me, endpoint=EDGE, p256dh="key-1", auth="auth-1"):
    # The same shape the browser's subscription.toJSON() gives, extra field included.
    body = {"endpoint": endpoint, "expirationTime": None, "keys": {"p256dh": p256dh, "auth": auth}}
    return client.post("/api/push/subscribe", json=body, headers=me)


def _unsubscribe(client, me, endpoint=EDGE):
    return client.request("DELETE", "/api/push/subscribe", json={"endpoint": endpoint}, headers=me)


def _rows() -> list[tuple[str, str, str]]:
    """Every saved browser as (owner's name, endpoint, p256dh)."""
    with SessionLocal() as db:
        return db.execute(
            select(User.name, PushSubscription.endpoint, PushSubscription.p256dh).join(
                User, User.id == PushSubscription.user_id
            )
        ).all()


def test_key_gives_the_public_key(client, monkeypatch):
    monkeypatch.setattr(settings, "vapid_public_key", "BPublicKey")
    response = client.get("/api/push/key")
    assert response.status_code == 200
    assert response.json() == {"public_key": "BPublicKey"}


def test_key_without_keys_in_env_is_503(client, monkeypatch):
    monkeypatch.setattr(settings, "vapid_public_key", "")
    assert client.get("/api/push/key").status_code == 503


def test_subscribe_saves_the_browser(client, sign_up):
    ben = sign_up("Ben")
    assert _subscribe(client, ben).status_code == 204
    assert _rows() == [("Ben", EDGE, "key-1")]


def test_subscribing_twice_from_one_browser_keeps_one_row(client, sign_up):
    ben = sign_up("Ben")
    _subscribe(client, ben)
    _subscribe(client, ben)
    assert len(_rows()) == 1


def test_subscribe_moves_an_existing_browser_to_the_new_user(client, sign_up):
    ben, ana = sign_up("Ben"), sign_up("Ana")
    _subscribe(client, ben)

    # Ana logs in on Ben's Edge: the same endpoint, maybe new keys.
    assert _subscribe(client, ana, p256dh="key-2").status_code == 204

    assert _rows() == [("Ana", EDGE, "key-2")]


def test_unsubscribe_deletes_my_own_browser(client, sign_up):
    ben = sign_up("Ben")
    _subscribe(client, ben)
    assert _unsubscribe(client, ben).status_code == 204
    assert _rows() == []


def test_unsubscribe_cannot_delete_someone_elses_browser(client, sign_up):
    ben, ana = sign_up("Ben"), sign_up("Ana")
    _subscribe(client, ben)

    # The same 204, so the reply doesn't tell Ana whose browser it is.
    assert _unsubscribe(client, ana).status_code == 204
    assert _rows() == [("Ben", EDGE, "key-1")]


def test_only_https_addresses_are_taken(client, sign_up):
    ben = sign_up("Ben")
    # The worker POSTs to this address, so nothing on our own machine.
    assert _subscribe(client, ben, endpoint="http://127.0.0.1:15672/api").status_code == 422
    assert _rows() == []


def test_push_routes_need_a_log_in(client):
    assert _subscribe(client, {}).status_code == 401
    assert _unsubscribe(client, {}).status_code == 401


def test_the_11th_subscribe_in_a_minute_gets_429(client, sign_up):
    ben = sign_up("Ben")
    assert [_subscribe(client, ben).status_code for _ in range(10)] == [204] * 10

    refused = _subscribe(client, ben)
    assert refused.status_code == 429
    assert 1 <= int(refused.headers["Retry-After"]) <= 60
