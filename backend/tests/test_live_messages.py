import uuid
from contextlib import contextmanager

from app.chats.service import mark_delivered, mark_read
from app.live import manager, routes


def _my_id(client, me) -> str:
    return client.get("/api/auth/me", headers=me).json()["id"]


def _start_chat(client, me, email) -> str:
    response = client.post("/api/chats/direct", json={"email": email}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _send(client, me, chat_id, body, client_msg_id=None):
    return client.post(
        f"/api/chats/{chat_id}/messages",
        json={"client_msg_id": str(client_msg_id or uuid.uuid4()), "body": body},
        headers=me,
    )


@contextmanager
def _open_line(client, me):
    """One open tab: get a ticket, open the line, read the hello."""
    ticket = client.post("/api/live/ticket", headers=me).json()["ticket"]
    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"
        yield line


class _DeadLine:
    """Stands in for a tab whose network died: every send fails."""

    async def send_text(self, text):
        raise RuntimeError("network gone")


def test_bens_line_gets_anas_new_message(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")

    with _open_line(client, ben) as bens_line:
        sent = _send(client, ana, chat_id, "hi Ben").json()

        # The same message the send replied with, no reload needed.
        assert bens_line.receive_json() == {"type": "message.new", "data": sent}


def test_bens_delivered_moves_his_bookmark_and_ana_gets_a_receipt(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = _my_id(client, ben)
    chat_id = _start_chat(client, ana, "ben@example.com")
    for body in ["one", "two"]:
        _send(client, ana, chat_id, body)

    with _open_line(client, ana) as anas_line, _open_line(client, ben) as bens_line:
        assert anas_line.receive_json()["type"] == "presence"  # Ben came online (T20)
        bens_line.send_json({"type": "delivered", "data": {"chat_id": chat_id, "seq": 2}})

        assert anas_line.receive_json() == {
            "type": "receipt",
            "data": {"chat_id": chat_id, "user_id": ben_id, "delivered_up_to": 2, "read_up_to": 0},
        }

    # After a reload, the history shows the same bookmark.
    members = client.get(f"/api/chats/{chat_id}/messages", headers=ana).json()["members"]
    assert {m["user_id"]: m["delivered_up_to"] for m in members}[ben_id] == 2


def test_bens_read_moves_both_bookmarks_and_ana_gets_a_receipt(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = _my_id(client, ben)
    chat_id = _start_chat(client, ana, "ben@example.com")
    for body in ["one", "two"]:
        _send(client, ana, chat_id, body)

    with _open_line(client, ana) as anas_line, _open_line(client, ben) as bens_line:
        assert anas_line.receive_json()["type"] == "presence"  # Ben came online (T20)
        bens_line.send_json({"type": "read", "data": {"chat_id": chat_id, "seq": 2}})

        # Read lifts delivered too, and the receipt carries both.
        assert anas_line.receive_json() == {
            "type": "receipt",
            "data": {"chat_id": chat_id, "user_id": ben_id, "delivered_up_to": 2, "read_up_to": 2},
        }

    # After a reload: the same bookmarks, and Ben's unread stays at 0.
    members = client.get(f"/api/chats/{chat_id}/messages", headers=ana).json()["members"]
    bens = next(m for m in members if m["user_id"] == ben_id)
    assert (bens["delivered_up_to"], bens["read_up_to"]) == (2, 2)
    assert client.get("/api/chats", headers=ben).json()[0]["unread"] == 0


def test_bens_other_tab_gets_his_own_read_receipt(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = _my_id(client, ben)
    chat_id = _start_chat(client, ana, "ben@example.com")
    _send(client, ana, chat_id, "hi Ben")

    with _open_line(client, ben) as bens_tab_1, _open_line(client, ben) as bens_tab_2:
        bens_tab_1.send_json({"type": "read", "data": {"chat_id": chat_id, "seq": 1}})

        # Tab 2 hears that Ben read #1 in tab 1, so it can clear its unread count (D20).
        assert bens_tab_2.receive_json() == {
            "type": "receipt",
            "data": {"chat_id": chat_id, "user_id": ben_id, "delivered_up_to": 1, "read_up_to": 1},
        }


def test_delivered_never_goes_backwards_or_past_the_last_message(client, sign_up, db):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = uuid.UUID(_my_id(client, ben))
    chat_id = uuid.UUID(_start_chat(client, ana, "ben@example.com"))
    for body in ["one", "two", "three"]:
        _send(client, ana, chat_id, body)

    # Both bookmarks come back: (delivered_up_to, read_up_to)
    assert mark_delivered(db, chat_id, ben_id, 2) == (2, 0)
    assert mark_delivered(db, chat_id, ben_id, 1) is None  # backwards: ignored
    assert mark_delivered(db, chat_id, ben_id, 99) == (3, 0)  # capped at #3, the last message
    assert mark_delivered(db, chat_id, ben_id, 99) is None  # already there: nothing moves


def test_read_moves_both_bookmarks_and_never_goes_backwards_or_past_the_last_message(client, sign_up, db):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = uuid.UUID(_my_id(client, ben))
    chat_id = uuid.UUID(_start_chat(client, ana, "ben@example.com"))
    for body in ["one", "two", "three"]:
        _send(client, ana, chat_id, body)

    assert mark_read(db, chat_id, ben_id, 2) == (2, 2)  # read implies delivered
    assert mark_read(db, chat_id, ben_id, 1) is None  # backwards: ignored
    assert mark_read(db, chat_id, ben_id, 99) == (3, 3)  # capped at #3, the last message
    assert mark_read(db, chat_id, ben_id, 99) is None  # already there: nothing moves


def test_read_never_pulls_delivered_back(client, sign_up, db):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = uuid.UUID(_my_id(client, ben))
    chat_id = uuid.UUID(_start_chat(client, ana, "ben@example.com"))
    for body in ["one", "two", "three"]:
        _send(client, ana, chat_id, body)

    mark_delivered(db, chat_id, ben_id, 3)  # all three reached his phone
    assert mark_read(db, chat_id, ben_id, 1) == (3, 1)  # he has only looked at #1


def test_sending_moves_both_of_the_senders_bookmarks(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")
    ana_id = _my_id(client, ana)
    chat_id = _start_chat(client, ana, "ben@example.com")

    _send(client, ana, chat_id, "hi")

    members = client.get(f"/api/chats/{chat_id}/messages", headers=ana).json()["members"]
    mine = next(m for m in members if m["user_id"] == ana_id)
    assert (mine["delivered_up_to"], mine["read_up_to"]) == (1, 1)


def test_a_non_members_delivered_and_read_are_ignored(client, sign_up, db):
    ana, cara = sign_up("Ana"), sign_up("Cara")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    _send(client, ana, chat_id, "just for Ben")
    cara_id = uuid.UUID(_my_id(client, cara))

    assert mark_delivered(db, uuid.UUID(chat_id), cara_id, 1) is None
    assert mark_read(db, uuid.UUID(chat_id), cara_id, 1) is None
    # Cara didn't sneak into the chat either.
    assert len(client.get(f"/api/chats/{chat_id}/messages", headers=ana).json()["members"]) == 2


def test_a_dead_line_doesnt_stop_bens_other_tab(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = uuid.UUID(_my_id(client, ben))
    chat_id = _start_chat(client, ana, "ben@example.com")

    with _open_line(client, ben) as bens_tab:
        dead_tab = _DeadLine()
        manager.connect(ben_id, dead_tab)

        assert _send(client, ana, chat_id, "still there?").status_code == 201

        assert bens_tab.receive_json()["data"]["body"] == "still there?"
        assert dead_tab not in manager.lines[ben_id]  # dropped from the switchboard


def test_a_repeated_send_pushes_nothing(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    client_msg_id = uuid.uuid4()

    with _open_line(client, ben) as bens_line:
        assert _send(client, ana, chat_id, "hi", client_msg_id).status_code == 201
        assert _send(client, ana, chat_id, "hi", client_msg_id).status_code == 200
        _send(client, ana, chat_id, "next one")

        # A test can't wait for "nothing", so: after #1, the next push must be #2, not #1 again.
        assert bens_line.receive_json()["data"]["seq"] == 1
        assert bens_line.receive_json()["data"]["seq"] == 2


def test_typing_reaches_ana_but_not_ben(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = _my_id(client, ben)
    chat_id = _start_chat(client, ana, "ben@example.com")

    with _open_line(client, ana) as anas_line, _open_line(client, ben) as bens_line:
        assert anas_line.receive_json()["type"] == "presence"  # Ben came online (T20)
        bens_line.send_json({"type": "typing", "data": {"chat_id": chat_id}})
        assert anas_line.receive_json() == {"type": "typing", "data": {"chat_id": chat_id, "user_id": ben_id}}

        # Ben's own line doesn't get it back: the next thing it gets is Ana's message.
        _send(client, ana, chat_id, "hi")
        assert bens_line.receive_json()["type"] == "message.new"


def test_a_non_members_typing_is_ignored(client, sign_up):
    ana, cara = sign_up("Ana"), sign_up("Cara")
    sign_up("Ben")
    bens_chat = _start_chat(client, ana, "ben@example.com")
    caras_chat = _start_chat(client, ana, "cara@example.com")
    _send(client, ana, caras_chat, "hi Cara")

    with _open_line(client, ana) as anas_line, _open_line(client, cara) as caras_line:
        assert anas_line.receive_json()["type"] == "presence"  # Cara came online (T20)
        caras_line.send_json({"type": "typing", "data": {"chat_id": bens_chat}})  # not her chat
        # A marker on the same line, so it's handled after the typing: her read in her own chat.
        caras_line.send_json({"type": "read", "data": {"chat_id": caras_chat, "seq": 1}})

        assert anas_line.receive_json()["type"] == "receipt"  # not "typing"


def test_a_second_typing_inside_one_second_is_dropped(client, sign_up, monkeypatch):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    _send(client, ana, chat_id, "hi")
    typing = {"type": "typing", "data": {"chat_id": chat_id}}

    with _open_line(client, ana) as anas_line, _open_line(client, ben) as bens_line:
        assert anas_line.receive_json()["type"] == "presence"  # Ben came online (T20)
        bens_line.send_json(typing)
        bens_line.send_json(typing)  # straight after: dropped
        bens_line.send_json({"type": "read", "data": {"chat_id": chat_id, "seq": 1}})  # a marker

        assert anas_line.receive_json()["type"] == "typing"
        assert anas_line.receive_json()["type"] == "receipt"  # not a second "typing"

        # Fake the clock: 1.1 seconds later, typing gets through again.
        later = routes._now() + 1.1
        monkeypatch.setattr(routes, "_now", lambda: later)
        bens_line.send_json(typing)
        assert anas_line.receive_json()["type"] == "typing"
