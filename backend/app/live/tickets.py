import secrets
import threading
import time
import uuid

TICKET_SECONDS = 30

# ticket -> (whose it is, when it dies). In memory for now; Redis in T21 (D19).
_tickets: dict[str, tuple[uuid.UUID, float]] = {}

# The ticket route runs in a worker thread, and the live line on the async
# side, so two of them can touch _tickets at the same moment. The lock lets
# only one in at a time.
_lock = threading.Lock()


def _now() -> float:
    """Seconds on a clock that only moves forward. Tests swap this to fake the time."""
    return time.monotonic()


def issue(user_id: uuid.UUID) -> str:
    """Make a random ticket for this user. It works once, within 30 seconds."""
    ticket = secrets.token_urlsafe(32)
    now = _now()
    with _lock:
        # Throw out tickets nobody used, so the list doesn't grow forever.
        for old in [t for t, (_, dies_at) in _tickets.items() if dies_at <= now]:
            del _tickets[old]
        _tickets[ticket] = (user_id, now + TICKET_SECONDS)
    return ticket


def redeem(ticket: str) -> uuid.UUID | None:
    """Cross the ticket off and return whose it was. None if it's unknown,
    already used or expired."""
    with _lock:
        # pop takes it out, so a second try finds nothing.
        entry = _tickets.pop(ticket, None)
    if entry is None:
        return None
    user_id, dies_at = entry
    if dies_at <= _now():
        return None
    return user_id
