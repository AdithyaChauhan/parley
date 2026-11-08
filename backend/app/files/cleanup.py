"""Files that were uploaded but never sent are removed after a day (D38)."""

import logging
import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.files.models import Upload
from app.files.s3 import StoreError
from app.files.store import configured, store

log = logging.getLogger(__name__)

UNSENT_AFTER = timedelta(days=1)
BATCH = 200
EVERY_SECONDS = 60 * 60


def remove_unsent(older_than: timedelta = UNSENT_AFTER) -> int:
    """Remove up to one batch of old unsent files. Returns how many went."""
    cutoff = datetime.now(UTC) - older_than
    with SessionLocal() as db:
        rows = list(
            db.execute(
                select(Upload.id, Upload.key)
                .where(Upload.message_id.is_(None), Upload.created_at < cutoff)
                .limit(BATCH)
            )
        )

    removed = []
    # The store first, then the row: if this stops halfway, the row is still
    # there, so the next run finishes the job.
    for upload_id, key in rows:
        try:
            store.delete(key)
        except StoreError as error:
            log.warning("Couldn't remove an unsent file, trying again next time: %s", error)
            break
        removed.append(upload_id)

    if removed:
        with SessionLocal() as db:
            # message_id checked again: a send can't reach a day-old upload in
            # practice, but this never removes a row that got a message.
            db.execute(delete(Upload).where(Upload.id.in_(removed), Upload.message_id.is_(None)))
            db.commit()
    return len(removed)


def _run(stop: threading.Event) -> None:
    while not stop.wait(EVERY_SECONDS):
        try:
            # Until a batch comes back short: nothing more is due.
            while remove_unsent() == BATCH:
                pass
        except Exception:
            # Never takes the worker down. The next hour tries again.
            log.exception("Removing unsent files failed")


def start(stop: threading.Event) -> None:
    """Runs in a small background thread, beside the worker's job loop."""
    if configured():
        threading.Thread(target=_run, args=(stop,), name="unsent-files", daemon=True).start()
