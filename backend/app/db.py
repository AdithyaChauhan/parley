from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# One number for three things on each backend copy (D34): database connections,
# threads (main.py) and requests at work at once (busy.py). A request at work
# then always finds a thread, and a thread always finds a connection, so none of
# them waits for another. With 40 threads and 15 connections they could wait for
# each other, which froze a copy in the load test (docs/load-test.md).
# Why 8: Python runs one thread at a time, so more threads don't go faster. The
# load test got the same messages/s with 5, 8 and 15, and 8 was the only one with
# no dropped live lines. PostgreSQL allows 100: 2 copies (16), plus worker, migrate
# and exporters (about 5), leaves plenty.
CAPACITY = 8

# pool_pre_ping: check a saved connection still works before using it,
# so the app recovers by itself after the database restarts.
# max_overflow=0: a steady pool, with no opening and closing under load.
# pool_timeout: a thread shouldn't ever wait (see above), so this is only a
# backstop: after 2 s the request gets 503 "busy" (main.py).
# connect_timeout: give up on a new connection after 5 seconds instead of
# waiting forever when the database is down.
# idle_in_transaction_session_timeout: the safety net (D34). PostgreSQL ends a
# session that sits in an open transaction for 60 s, so nothing stuck can hold a
# lock forever.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=CAPACITY,
    max_overflow=0,
    pool_timeout=2,
    connect_args={
        "connect_timeout": 5,
        "options": "-c idle_in_transaction_session_timeout=60s",
    },
)

# Open a session with "with SessionLocal() as db:" inside the work itself, and
# close it before any wait, so a request never holds a connection while it waits
# for a thread, Redis or RabbitMQ (D34).
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass
