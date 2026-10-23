import logging
import uuid

from app.config import settings

log = logging.getLogger(__name__)


class NotifyFailed(Exception):
    """The notifier couldn't reach the person. The worker retries later."""


class LogNotifier:
    """Today's notifier: one log line. T24 swaps in real browser push with the
    same send(). Never any message text, only who it's from (D12)."""

    def send(self, user_id: uuid.UUID, user_name: str, title: str) -> None:
        log.info("notify %s: %s", user_name, title)


def fake_fail(attempt: int) -> None:
    """For demos and tests: with NOTIFY_FAKE_FAIL_TIMES=N, tries 1 to N fail
    on purpose, as if the push service were down."""
    if attempt <= settings.notify_fake_fail_times:
        raise NotifyFailed(f"fake fail ({attempt} of {settings.notify_fake_fail_times})")
