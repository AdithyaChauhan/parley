"""Statuses run out after 24 hours (D41). Reads already stop at that moment;
this removes the rows and photos afterwards, once an hour in the worker."""

import logging
import threading
import uuid
from datetime import timedelta

from sqlalchemy import delete, or_, select

from app.db import SessionLocal
from app.files.s3 import StoreError
from app.files.store import configured, store
from app.status.models import Status
from app.status.service import now

log = logging.getLogger(__name__)

# A photo that was uploaded but never posted, like an unsent file (D38).
UNPOSTED_AFTER = timedelta(days=1)
BATCH = 200
EVERY_SECONDS = 60 * 60


def _drop(rows: list[tuple[uuid.UUID, dict | None]]) -> int:
    """The photo from the store first, then the row. If the store is down, the
    row stays, so the next run tries again."""
    removed = []
    for status_id, data in rows:
        key = (data or {}).get("key")
        if key and configured():
            try:
                store.delete(key)
            except StoreError as error:
                log.warning("Couldn't remove a status photo, trying again next time: %s", error)
                break
        removed.append(status_id)
    if removed:
        with SessionLocal() as db:
            db.execute(delete(Status).where(Status.id.in_(removed)))
            db.commit()
    return len(removed)


def erase(status_id: uuid.UUID) -> None:
    """A status deleted by its poster: gone now if the store answers, else next hour."""
    with SessionLocal() as db:
        row = db.execute(select(Status.id, Status.data).where(Status.id == status_id)).first()
    if row is not None:
        _drop([tuple(row)])


def remove_expired() -> int:
    """One batch of run-out statuses, and photos never posted. Returns how many went."""
    with SessionLocal() as db:
        rows = db.execute(
            select(Status.id, Status.data)
            .where(
                or_(
                    Status.expires_at <= now(),
                    Status.posted_at.is_(None) & (Status.created_at < now() - UNPOSTED_AFTER),
                )
            )
            .limit(BATCH)
        ).all()
    return _drop([tuple(row) for row in rows])


def _run(stop: threading.Event) -> None:
    while not stop.wait(EVERY_SECONDS):
        try:
            # Until a batch comes back short: nothing more is due.
            while remove_expired() == BATCH:
                pass
        except Exception:
            # Never takes the worker down. The next hour tries again.
            log.exception("Removing run-out statuses failed")


def start(stop: threading.Event) -> None:
    """Runs in a small background thread, beside the worker's job loop. Also
    without a store: text statuses need removing too."""
    threading.Thread(target=_run, args=(stop,), name="statuses", daemon=True).start()
