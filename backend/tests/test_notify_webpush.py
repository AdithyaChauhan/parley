import json
import logging
import os
import time
import uuid

import http_ece
import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid
from py_vapid.utils import b64urlencode
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.notify import queues, worker
from app.notify.notifier import (
    NOTIFIED_SECONDS,
    LogNotifier,
    NotifyFailed,
    WebPushNotifier,
    make_notifier,
)
from app.notify.queues import Job
from app.presence import service as presence
from app.push.models import PushSubscription

EDGE = "https://fcm.googleapis.com/fcm/send/ben-edge"
FIREFOX = "https://updates.push.services.mozilla.com/wpush/v2/ben-firefox"


class FakePushService:
    """Stands in for Google's and Mozilla's push services, so no test ever
    touches the network. Answers 201 unless told otherwise, per address:
    a status code, or an error to raise (like a timeout). Keeps every POST."""

    def __init__(self):
        self.answers: dict[str, int | Exception] = {}
        self.posts: list[dict] = []

    def post(self, url, data=None, headers=None, timeout=None, **_):
        self.posts.append({"url": url, "data": data, "headers": headers, "timeout": timeout})
        answer = self.answers.get(url, 201)
        if isinstance(answer, Exception):
            raise answer
        response = requests.Response()
        response.status_code = answer
        response._content = b""
        return response

    def urls(self) -> list[str]:
        return [post["url"] for post in self.posts]


class Browser:
    """A pretend browser: its own key pair and auth secret, like the ones a
    real browser hands over when it subscribes. It can open its pushes."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.auth = os.urandom(16)
        public = self.private_key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        self.keys = {"p256dh": b64urlencode(public), "auth": b64urlencode(self.auth)}

    def open(self, post: dict) -> dict:
        """Unlock a push sent to this browser. Only its private key can."""
        return json.loads(http_ece.decrypt(post["data"], private_key=self.private_key, auth_secret=self.auth))


@pytest.fixture(autouse=True)
def vapid(monkeypatch, caplog):
    """Throwaway VAPID keys for each test (D26), never the ones in .env."""
    keys = Vapid()
    keys.generate_keys()
    monkeypatch.setattr(settings, "vapid_private_key", b64urlencode(keys.private_key.private_numbers().private_value.to_bytes(32, "big")))
    monkeypatch.setattr(settings, "vapid_subject", "mailto:test@example.com")
    monkeypatch.setattr(worker, "IDLE_SECONDS", 0.1)
    caplog.set_level(logging.INFO)


@pytest.fixture
def push_service():
    return FakePushService()


@pytest.fixture
def notifier(push_service):
    return WebPushNotifier(presence.client, session=push_service)


def _ben_with(client, sign_up, *browsers: Browser) -> uuid.UUID:
    """Sign Ben up and subscribe each browser for him. Returns Ben's id."""
    ben = sign_up("Ben")
    for browser in browsers:
        body = {"endpoint": browser.endpoint, "keys": browser.keys}
        assert client.post("/api/push/subscribe", json=body, headers=ben).status_code == 204
    return uuid.UUID(client.get("/api/auth/me", headers=ben).json()["id"])


def _job(ben_id: uuid.UUID) -> Job:
    return Job(message_id=uuid.uuid4(), chat_id=uuid.uuid4(), seq=1, recipient_id=ben_id)


def _device_id(endpoint: str) -> uuid.UUID | None:
    with SessionLocal() as db:
        return db.scalar(select(PushSubscription.id).where(PushSubscription.endpoint == endpoint))


def _send(notifier, job):
    return notifier.send(job, "Ben", "New message from Ana")


# --- One device ---


def test_201_sends_and_notes_that_device(client, sign_up, notifier, push_service):
    ben_id = _ben_with(client, sign_up, Browser(EDGE))
    job = _job(ben_id)

    assert _send(notifier, job) == "sent"

    assert push_service.urls() == [EDGE]
    key = f"notified:{job.message_id}:{_device_id(EDGE)}"
    assert 0 < presence.client.ttl(key) <= NOTIFIED_SECONDS


def test_the_same_job_again_is_not_pushed_twice(client, sign_up, notifier, push_service):
    ben_id = _ben_with(client, sign_up, Browser(EDGE))
    job = _job(ben_id)
    _send(notifier, job)

    assert _send(notifier, job) == "skip: already notified"
    assert push_service.urls() == [EDGE]


def test_the_push_is_the_title_and_chat_only_with_a_1_hour_ttl(client, sign_up, notifier, push_service):
    edge = Browser(EDGE)
    job = _job(_ben_with(client, sign_up, edge))

    _send(notifier, job)

    [post] = push_service.posts
    # Opened with the browser's own key: exactly these two things, nothing else (D12).
    assert edge.open(post) == {"title": "New message from Ana", "chat_id": str(job.chat_id)}
    assert post["headers"]["ttl"] == "3600"
    # Signed with our VAPID key, and never waiting forever.
    assert post["headers"]["authorization"].startswith("vapid ")
    assert post["timeout"] == 10


@pytest.mark.parametrize("status", [404, 410])
def test_404_or_410_deletes_the_device_and_does_not_retry(client, sign_up, notifier, push_service, status):
    job = _job(_ben_with(client, sign_up, Browser(EDGE)))
    push_service.answers[EDGE] = status

    # No NotifyFailed: nothing to retry. Ben has no devices left.
    assert _send(notifier, job) == "skip: no devices"
    assert _device_id(EDGE) is None


@pytest.mark.parametrize(
    "answer",
    [500, 503, 429, 403, 400, requests.Timeout("too slow"), requests.ConnectionError("can't reach it")],
    ids=["500", "503", "429", "403 wrong VAPID key", "400", "timeout", "can't connect"],
)
def test_anything_else_raises_notify_failed_so_the_worker_retries(client, sign_up, notifier, push_service, answer):
    job = _job(_ben_with(client, sign_up, Browser(EDGE)))
    push_service.answers[EDGE] = answer

    with pytest.raises(NotifyFailed):
        _send(notifier, job)

    # Not noted, and the device is kept: the retry tries it again.
    assert not presence.client.exists(f"notified:{job.message_id}:{_device_id(EDGE)}")
    assert _device_id(EDGE) is not None


def test_a_user_with_no_devices_is_skipped(client, sign_up, notifier, push_service):
    job = _job(_ben_with(client, sign_up))
    assert _send(notifier, job) == "skip: no devices"
    assert push_service.posts == []


# --- Two devices ---


def test_two_devices_one_500_the_retry_only_tries_the_failed_one(client, sign_up, notifier, push_service):
    job = _job(_ben_with(client, sign_up, Browser(EDGE), Browser(FIREFOX)))
    push_service.answers[FIREFOX] = 500

    with pytest.raises(NotifyFailed, match="push service said 500"):
        _send(notifier, job)
    assert sorted(push_service.urls()) == sorted([EDGE, FIREFOX])

    # Firefox's push service is fine again. Edge already showed it: skipped.
    push_service.answers[FIREFOX] = 201
    push_service.posts.clear()
    assert _send(notifier, job) == "sent"
    assert push_service.urls() == [FIREFOX]


def test_one_device_gone_the_other_still_gets_it(client, sign_up, notifier, push_service):
    job = _job(_ben_with(client, sign_up, Browser(EDGE), Browser(FIREFOX)))
    push_service.answers[EDGE] = 410

    assert _send(notifier, job) == "sent"
    assert _device_id(EDGE) is None
    assert _device_id(FIREFOX) is not None


# --- Picking the notifier ---


def test_the_setting_picks_the_notifier(monkeypatch):
    monkeypatch.setattr(settings, "notifier", "log")
    assert isinstance(make_notifier(presence.client), LogNotifier)
    monkeypatch.setattr(settings, "notifier", "webpush")
    assert isinstance(make_notifier(presence.client), WebPushNotifier)


def test_webpush_without_keys_refuses_to_start(monkeypatch):
    monkeypatch.setattr(settings, "vapid_private_key", "")
    with pytest.raises(RuntimeError, match="VAPID"):
        WebPushNotifier(presence.client)


# --- The whole way: send → RabbitMQ → worker → push ---


def test_through_the_worker_no_message_text_and_a_retry_for_the_failed_device(
    client, sign_up, rabbit, push_service, monkeypatch, caplog
):
    edge, firefox = Browser(EDGE), Browser(FIREFOX)
    _ben_with(client, sign_up, edge, firefox)
    ana = sign_up("Ana")
    chat_id = client.post("/api/chats/direct", json={"email": "ben@example.com"}, headers=ana).json()["id"]
    client.post(
        f"/api/chats/{chat_id}/messages",
        json={"client_msg_id": str(uuid.uuid4()), "body": "meet me at 6"},
        headers=ana,
    )
    monkeypatch.setattr(worker, "notifier", WebPushNotifier(worker.redis_client, session=push_service))
    push_service.answers[FIREFOX] = 500

    # Try 1: Edge gets it, Firefox fails. Then 0.1 s in the retry box (test timers), try 2.
    deadline = time.monotonic() + 10
    worker.consume(rabbit, should_stop=lambda: "try 2:" in caplog.text or time.monotonic() > deadline)
    assert "try 1: failed (NotifyFailed: device" in caplog.text
    # Firefox still says 500 on try 2, so Edge must have been skipped then.
    assert push_service.urls().count(EDGE) == 1

    push_service.answers[FIREFOX] = 201
    deadline = time.monotonic() + 10
    worker.consume(rabbit, should_stop=lambda: "try 3: sent" in caplog.text or time.monotonic() > deadline)
    assert "try 3: sent" in caplog.text
    assert push_service.urls().count(EDGE) == 1

    # Every push, opened with its browser's key: who it's from, never what they said.
    for post in push_service.posts:
        browser = edge if post["url"] == EDGE else firefox
        opened = browser.open(post)
        assert opened == {"title": "New message from Ana", "chat_id": chat_id}
        assert "meet me" not in json.dumps(opened)
