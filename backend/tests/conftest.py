import os
from pathlib import Path
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.config import Config
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import make_url, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR.parent / ".env"


class _TestSettings(BaseSettings):
    # Reads TEST_DATABASE_URL and TEST_REDIS_URL from the shell (CI) or from .env (laptop).
    # We can't use app.config here: importing it would build the app's
    # settings with the real DATABASE_URL before we get to change it.
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    test_database_url: str
    test_redis_url: str


_test_settings = _TestSettings()
TEST_DATABASE_URL = _test_settings.test_database_url
TEST_REDIS_URL = _test_settings.test_redis_url

# The tests empty tables, so refuse to run against anything but a test database.
if not make_url(TEST_DATABASE_URL).database.endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must point at a database whose name ends in _test")

# The same for Redis: the tests wipe it, so only database number 15 is allowed (D22).
if urlparse(TEST_REDIS_URL).path != "/15":
    raise RuntimeError("TEST_REDIS_URL must point at Redis database 15, like redis://localhost:6379/15")

# The app reads DATABASE_URL once, when it is first imported. A real
# environment variable wins over .env, so setting it here, before any test
# imports the app, points the whole app at the test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL

from fastapi.testclient import TestClient  # noqa: E402  (must come after the line above)

from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.presence import service as presence  # noqa: E402


def _empty_all_tables():
    """Empties every sheet and wipes Redis, so the next test starts clean."""
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users, sessions, chats, chat_members, messages"))
    # And the whiteboard: every presence and last seen note (Redis database 15).
    presence.client.flushdb()


@pytest.fixture(scope="session")
def test_database():
    """Build the tables once per test run, with the same migrations as the real database."""
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")


@pytest.fixture
def client(test_database):
    """A fresh test browser for one test. Empties every sheet afterwards,
    so every test starts clean."""
    # "with": one event loop for the whole test, so an HTTP send can push
    # to a live line the same test opened.
    with TestClient(app) as test_client:
        yield test_client

    _empty_all_tables()


@pytest.fixture
def sign_up(client):
    """Makes an account and returns its login header, like Authorize in /docs.
    sign_up("Ana") makes ana@example.com."""

    def _sign_up(name: str) -> dict[str, str]:
        response = client.post(
            "/api/auth/signup",
            json={"name": name, "email": f"{name.lower()}@example.com", "password": "secret123"},
        )
        assert response.status_code == 201
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _sign_up


@pytest.fixture
def db(test_database):
    """A database session, for tests that skip the routes. Empties every
    sheet afterwards, so every test starts clean."""
    with SessionLocal() as session:
        yield session

    _empty_all_tables()
