from contextlib import contextmanager
from datetime import UTC, datetime

from app.presence import service as presence


def _my_id(client, me) -> str:
    return client.get("/api/auth/me", headers=me).json()["id"]


def _start_chat(client, me, email) -> str:
    response = client.post("/api/chats/direct", json={"email": email}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


@contextmanager
def _open_line(client, me):
    """One open tab: get a ticket, open the line, read the hello."""
    ticket = client.post("/api/live/ticket", headers=me).json()["ticket"]
    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"
        yield line


def _anas_row(client, ben) -> dict:
    """Ana's row in Ben's chat list (his only chat)."""
    return client.get("/api/chats", headers=ben).json()[0]


def test_one_tab_is_online_and_closing_it_is_offline(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    _start_chat(client, ana, "ben@example.com")
    assert _anas_row(client, ben)["online"] is False

    with _open_line(client, ana):
        assert _anas_row(client, ben)["online"] is True

    assert _anas_row(client, ben)["online"] is False


def test_closing_one_of_two_tabs_stays_online(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    _start_chat(client, ana, "ben@example.com")

    with _open_line(client, ana):
        with _open_line(client, ana):
            assert _anas_row(client, ben)["online"] is True
        # The second tab closed; the first one is still open.
        assert _anas_row(client, ben)["online"] is True

    assert _anas_row(client, ben)["online"] is False


def test_a_silent_tab_goes_offline_when_its_time_passes(client, sign_up, monkeypatch):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    _start_chat(client, ana, "ben@example.com")

    with _open_line(client, ana):
        assert _anas_row(client, ben)["online"] is True

        # The line stays open but no ping comes (a paused or crashed tab).
        # Fake the clock: jump 61 seconds ahead instead of waiting.
        later = presence._now() + 61
        monkeypatch.setattr(presence, "_now", lambda: later)

        assert _anas_row(client, ben)["online"] is False


def test_a_ping_keeps_a_tab_alive(client, sign_up, monkeypatch):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    _start_chat(client, ana, "ben@example.com")
    start = presence._now()

    with _open_line(client, ana) as anas_line:
        # 50 s later, a ping: the tab is now alive until 110 s.
        monkeypatch.setattr(presence, "_now", lambda: start + 50)
        anas_line.send_json({"type": "ping"})
        assert anas_line.receive_json()["type"] == "pong"

        # 100 s after hello: past the first 60 s, but not past the ping's.
        monkeypatch.setattr(presence, "_now", lambda: start + 100)
        assert _anas_row(client, ben)["online"] is True


def test_last_seen_is_set(client, sign_up, monkeypatch):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    _start_chat(client, ana, "ben@example.com")
    assert _anas_row(client, ben)["last_seen"] is None  # never seen yet

    # A fixed clock, so we know the exact time to expect.
    closed_at = datetime(2026, 10, 23, 11, 15, tzinfo=UTC)
    monkeypatch.setattr(presence, "_now", lambda: closed_at.timestamp())
    with _open_line(client, ana):
        pass

    row = _anas_row(client, ben)
    assert row["online"] is False
    assert datetime.fromisoformat(row["last_seen"]) == closed_at


def test_coming_online_and_going_offline_reach_a_partner_but_not_a_stranger(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    ana_id = _my_id(client, ana)
    _start_chat(client, ana, "ben@example.com")  # Cara shares no chat with Ana

    with _open_line(client, ben) as bens_line, _open_line(client, cara) as caras_line:
        with _open_line(client, ana) as anas_line:
            came = bens_line.receive_json()
            assert came["type"] == "presence"
            assert came["data"]["user_id"] == ana_id
            assert came["data"]["online"] is True
            assert came["data"]["last_seen"] is not None

            # A ping while already online is no news: the next thing Ben gets is the goodbye.
            anas_line.send_json({"type": "ping"})
            assert anas_line.receive_json()["type"] == "pong"

        went = bens_line.receive_json()
        assert went["type"] == "presence"
        assert went["data"]["user_id"] == ana_id
        assert went["data"]["online"] is False
        assert went["data"]["last_seen"] is not None

        # A test can't wait for "nothing", so: Cara pings, and the next thing
        # she gets is her pong, not Ana's news.
        caras_line.send_json({"type": "ping"})
        assert caras_line.receive_json()["type"] == "pong"


def test_the_chat_list_and_starting_a_chat_show_online_and_last_seen(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    _start_chat(client, ana, "ben@example.com")

    with _open_line(client, ana):
        row = _anas_row(client, ben)
        assert row["other_user_id"] == _my_id(client, ana)  # so presence news finds this row
        assert row["online"] is True
        assert row["last_seen"] is not None

        # Ben "starts" the chat that already exists: the same row, the same fields.
        again = client.post("/api/chats/direct", json={"email": "ana@example.com"}, headers=ben)
        assert again.status_code == 200
        assert again.json()["online"] is True

