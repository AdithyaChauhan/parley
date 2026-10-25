import json
import logging

import redis
import requests
from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select

from app.config import settings
from app.db import SessionLocal
from app.notify.queues import Job
from app.push.models import PushSubscription

log = logging.getLogger(__name__)

# "Already notified" notes last a day: long past any retry (D25).
NOTIFIED_SECONDS = 24 * 60 * 60
# A notification an hour late is useless: the push service drops it after this (D26).
PUSH_TTL_SECONDS = 60 * 60
# pywebpush waits forever by default. Each push gets at most this long (D26).
PUSH_TIMEOUT_SECONDS = 10


class NotifyFailed(Exception):
    """The notifier couldn't reach the person. The worker retries later."""


class DeviceGone(Exception):
    """The push service says this browser unsubscribed or was reset (404/410).
    No retry can fix that."""


def _note(redis_client: redis.Redis, key: str) -> None:
    """Write an "already notified" note, right after a successful send."""
    try:
        redis_client.set(key, 1, ex=NOTIFIED_SECONDS)
    except redis.RedisError:
        # Already sent, so don't fail the job: a retry would notify them again (D25).
        log.warning("Sent, but couldn't note it in Redis: %s", key)


class LogNotifier:
    """One log line instead of a push: for tests, CI and fake-fail demos.
    One note per person (D25), since a log line has no devices."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def send(self, job: Job, user_name: str, title: str) -> str:
        key = f"notified:{job.message_id}:{job.recipient_id}"
        if self.redis.exists(key):
            return "skip: already notified"  # this job ran before, then came back
        # Never any message text, only who it's from (D12).
        log.info("notify %s: %s", user_name, title)
        _note(self.redis, key)
        return "sent"


class WebPushNotifier:
    """Real browser notifications (D26): one push to each of the person's
    devices, with one note per device."""

    def __init__(self, redis_client: redis.Redis, session: requests.Session | None = None):
        if not (settings.vapid_private_key and settings.vapid_subject):
            raise RuntimeError("NOTIFIER=webpush needs VAPID_PRIVATE_KEY and VAPID_SUBJECT in .env")
        self.redis = redis_client
        # One session reuses connections to the push services. Tests hand in
        # a fake one, so no push ever leaves the laptop.
        self.session = session or requests.Session()

    def send(self, job: Job, user_name: str, title: str) -> str:
        with SessionLocal() as db:
            devices = db.scalars(
                select(PushSubscription).where(PushSubscription.user_id == job.recipient_id)
            ).all()
        if not devices:
            return "skip: no devices"

        # The title and the chat only, never the message text (D12). The
        # service worker uses chat_id as the notification's tag.
        payload = json.dumps({"title": title, "chat_id": str(job.chat_id)})
        sent = gone = 0
        failures = []
        for device in devices:
            key = f"notified:{job.message_id}:{device.id}"
            if self.redis.exists(key):
                continue  # this device got it on an earlier try
            try:
                self._push(device, payload)
            except DeviceGone:
                self._forget(device)
                gone += 1
            except NotifyFailed as error:
                # Keep going: the other devices still get theirs now.
                failures.append(f"device {str(device.id)[:8]}: {error}")
            else:
                _note(self.redis, key)
                sent += 1

        if failures:
            # The worker retries the whole job, and the devices noted above
            # are skipped then, so only the failed ones are tried again.
            raise NotifyFailed("; ".join(failures))
        if sent:
            return "sent"
        if gone == len(devices):
            return "skip: no devices"  # every one of them was gone
        return "skip: already notified"

    def _push(self, device: PushSubscription, payload: str) -> None:
        """Lock the payload for this browser, sign it, POST it to its push service."""
        try:
            webpush(
                subscription_info={"endpoint": device.endpoint, "keys": {"p256dh": device.p256dh, "auth": device.auth}},
                data=payload,
                vapid_private_key=settings.vapid_private_key,
                # A fresh dict every time: pywebpush writes this push service's
                # address into it, and a reused one would be wrong for the next.
                vapid_claims={"sub": settings.vapid_subject},
                ttl=PUSH_TTL_SECONDS,
                timeout=PUSH_TIMEOUT_SECONDS,
                requests_session=self.session,
            )
        except WebPushException as error:
            # 404/410 is the only final answer. Everything else retries and is
            # parked after try 4: 429, 5xx, and other 4xx like a wrong VAPID
            # key (403), so after fixing .env, replay sends them (D26).
            if error.status_code in (404, 410):
                raise DeviceGone from error
            raise NotifyFailed(f"push service said {error.status_code or error.message}") from error
        except requests.RequestException as error:
            # A timeout, or the push service can't be reached at all.
            raise NotifyFailed(type(error).__name__) from error

    def _forget(self, device: PushSubscription) -> None:
        """Delete a browser that's gone, so we stop pushing to it (D26)."""
        with SessionLocal() as db:
            db.execute(delete(PushSubscription).where(PushSubscription.id == device.id))
            db.commit()
        log.info("device %s is gone (404/410): deleted", str(device.id)[:8])


def make_notifier(redis_client: redis.Redis) -> LogNotifier | WebPushNotifier:
    """The setting NOTIFIER picks which one the worker uses (D26)."""
    if settings.notifier == "webpush":
        return WebPushNotifier(redis_client)
    return LogNotifier(redis_client)


def fake_fail(attempt: int) -> None:
    """For demos and tests: with NOTIFY_FAKE_FAIL_TIMES=N, tries 1 to N fail
    on purpose, as if the push service were down."""
    if attempt <= settings.notify_fake_fail_times:
        raise NotifyFailed(f"fake fail ({attempt} of {settings.notify_fake_fail_times})")
