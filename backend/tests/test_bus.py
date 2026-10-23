import json
import time
from contextlib import contextmanager

from app.live import bus
from app.presence import service as presence


def _my_id(client, me) -> str:
    return client.get("/api/auth/me", headers=me).json()["id"]


@contextmanager
def _open_line(client, me):
    """One open tab: get a ticket, open the line, read the hello."""
    ticket = client.post("/api/live/ticket", headers=me).json()["ticket"]
    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"
        yield line


def _listeners(channel: str) -> int:
    """How many Redis connections listen on this channel (PUBSUB NUMSUB)."""
    return dict(presence.client.pubsub_numsub(channel))[channel]


def _wait_for_no_listeners(channel: str) -> int:
    """The "stop listening" goes to Redis on the radio's own connection, so
    give Redis a moment to handle it. Returns the last count."""
    for _ in range(50):
        if _listeners(channel) == 0:
            return 0
        time.sleep(0.02)
    return _listeners(channel)


def test_a_shout_from_another_copy_reaches_bens_line(client, sign_up):
    ben = sign_up("Ben")
    ben_id = _my_id(client, ben)
    event = {"type": "typing", "data": {"chat_id": "made-up", "user_id": "someone"}}

    with _open_line(client, ben) as bens_line:
        # Exactly what copy A does when Ben's line is on copy B: shout on his channel.
        presence.client.publish(f"user:{ben_id}", json.dumps(event))

        assert bens_line.receive_json() == event


def test_this_copy_listens_for_ben_only_while_he_has_a_line_here(client, sign_up):
    ben = sign_up("Ben")
    ben_id = _my_id(client, ben)
    channel = f"user:{ben_id}"
    assert _listeners(channel) == 0

    with _open_line(client, ben):
        # Confirmed before hello, so Redis already knows.
        assert _listeners(channel) == 1
        with _open_line(client, ben):
            assert _listeners(channel) == 1  # one radio per copy, not one per tab
        # One tab closed, one still open: still listening.
        assert channel in bus._listening
        assert _listeners(channel) == 1

    # His last tab here closed: this copy stops listening for him.
    assert channel not in bus._listening
    assert _wait_for_no_listeners(channel) == 0


def test_the_radio_keeps_going_after_a_bad_event(client, sign_up):
    ben = sign_up("Ben")
    ben_id = _my_id(client, ben)
    good = {"type": "typing", "data": {"chat_id": "made-up", "user_id": "someone"}}

    with _open_line(client, ben) as bens_line:
        presence.client.publish(f"user:{ben_id}", "not json at all")
        presence.client.publish(f"user:{ben_id}", json.dumps(["not", "an", "event"]))
        presence.client.publish(f"user:{ben_id}", json.dumps(good))

        # The two bad ones were skipped, and the radio still delivered the good one.
        assert bens_line.receive_json() == good
