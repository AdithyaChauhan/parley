"""Makes the load test's own database, parley_load, from scratch (D33):
1,000 fake users, 500 direct chats (load0001 with load0002, load0003 with
load0004, ...), and one saved session per user. It runs inside the backend
image, before every run (bash loadtest/run.sh does it), so every run starts
from empty chats.
With LOAD_GROUP=50 (scenario f), users 1-50 also share one group (D37)."""

import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, insert, make_url, text

from app.auth.models import User, UserSession
from app.auth.security import REFRESH_TOKEN_DAYS, hash_password, hash_refresh_token
from app.chats.models import Chat, ChatMember
from app.chats.service import direct_key
from app.config import settings

USERS = 1_000
# Every fake user has the same password, so k6 knows it (logins.js). These
# accounts exist only in parley_load on the laptop.
PASSWORD = "load-test-password"
# The raw refresh tokens, one per user, in order (load0001 first). k6 reads
# them; git ignores the file, and the database only gets their fingerprints.
SESSIONS_FILE = Path(__file__).with_name("sessions.json")
# Scenario f: how many users share one group (0 = no group).
GROUP_SIZE = int(os.environ.get("LOAD_GROUP", "0"))


def email(n: int) -> str:
    """1 -> load0001@example.com"""
    return f"load{n:04d}@example.com"


def main() -> None:
    url = make_url(settings.database_url)
    # This wipes the database first, so it refuses any other one (D33).
    if not url.database.endswith("_load"):
        raise SystemExit(f"Refusing to seed {url.database!r}: the name must end in _load")

    # A database can't drop itself, so connect to Postgres's built-in one for
    # that. AUTOCOMMIT: Postgres won't create or drop a database inside a transaction.
    server = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        # FORCE: also cuts off anything still connected to it.
        connection.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    server.dispose()

    # The same tables as everywhere else, from the same migrations.
    command.upgrade(Config("alembic.ini"), "head")

    # One hash for everyone: argon2 is slow on purpose, and 1,000 of them
    # would take minutes (D33).
    password_hash = hash_password(PASSWORD)
    users = [
        {"id": uuid.uuid4(), "email": email(n), "name": f"Load {n:04d}", "password_hash": password_hash}
        for n in range(1, USERS + 1)
    ]
    chats, members = [], []
    # Pairs: users 1+2, 3+4, ... Each pair gets one direct chat.
    for a, b in zip(users[0::2], users[1::2]):
        chat_id = uuid.uuid4()
        chats.append({"id": chat_id, "kind": "direct", "direct_key": direct_key(a["id"], b["id"])})
        members += [{"chat_id": chat_id, "user_id": a["id"]}, {"chat_id": chat_id, "user_id": b["id"]}]

    # Scenario f: one group of the first GROUP_SIZE users, load0001 its admin.
    # Everyone sees it from #1 (D37). Kept apart: a bulk insert takes its
    # columns from the first row, so these extra ones (title, role) need their own.
    group_id = uuid.uuid4()
    group = {"id": group_id, "kind": "group", "title": "Load group"}
    group_members = [
        {"chat_id": group_id, "user_id": user["id"], "role": "admin" if n == 0 else "member"}
        for n, user in enumerate(users[:GROUP_SIZE])
    ]

    # A saved session per user, like a browser that's already logged in (D33).
    # k6 trades each token at /api/auth/refresh, so no fake user needs the slow
    # password check. Only the fingerprint goes in the database (D16).
    tokens = [secrets.token_urlsafe(32) for _ in users]
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS)
    sessions = [
        {"user_id": user["id"], "refresh_token_hash": hash_refresh_token(token), "expires_at": expires_at}
        for user, token in zip(users, tokens)
    ]

    # Straight into the tables, all in one transaction: about a second, where
    # 1,000 sign-ups would take minutes (and hit D24's per-IP limit).
    with create_engine(url).begin() as connection:
        connection.execute(insert(User), users)
        connection.execute(insert(Chat), chats)
        connection.execute(insert(ChatMember), members)
        if GROUP_SIZE:
            connection.execute(insert(Chat), [group])
            connection.execute(insert(ChatMember), group_members)
        connection.execute(insert(UserSession), sessions)
    SESSIONS_FILE.write_text(json.dumps(tokens))

    extra = f", one group of {GROUP_SIZE}" if GROUP_SIZE else ""
    print(f"{url.database}: {len(users)} users, {len(chats)} chats{extra}, {len(sessions)} sessions")


if __name__ == "__main__":
    main()
