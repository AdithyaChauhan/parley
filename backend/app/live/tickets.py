import secrets
import uuid

# The Redis clients made in T20 (D22). Used as presence.client and
# presence.async_client, because the async one is only made when the app starts.
from app.presence import service as presence

TICKET_SECONDS = 30


def _key(ticket: str) -> str:
    return f"ticket:{ticket}"


def issue(user_id: uuid.UUID) -> str:
    """Make a random ticket for this user. It works once, within 30 seconds.
    It lives in Redis, so any backend copy can redeem it (D23)."""
    ticket = secrets.token_urlsafe(32)
    # ex: Redis's own timer wipes it after 30 s, so nobody has to clean up.
    presence.client.set(_key(ticket), str(user_id), ex=TICKET_SECONDS)
    return ticket


async def redeem(ticket: str) -> uuid.UUID | None:
    """Cross the ticket off and return whose it was. None if it's unknown,
    already used or expired."""
    # GETDEL reads and deletes in one step: if two copies try the same ticket
    # at the same moment, only one of them gets the user id.
    user_id = await presence.async_client.getdel(_key(ticket))
    return None if user_id is None else uuid.UUID(user_id)
