import uuid
from contextlib import contextmanager

from app.chats.service import mark_delivered
from app.live import manager


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
        bens_line.send_json({"type": "delivered", "data": {"chat_id": chat_id, "seq": 2}})

        assert anas_line.receive_json() == {
            "type": "receipt",
            "data": {"chat_id": chat_id, "user_id": ben_id, "delivered_up_to": 2},
        }

    # After a reload, the history shows the same bookmark.
    members = client.get(f"/api/chats/{chat_id}/messages", headers=ana).json()["members"]
    assert {m["user_id"]: m["delivered_up_to"] for m in members}[ben_id] == 2


def test_delivered_never_goes_backwards_or_past_the_last_message(client, sign_up, db):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = uuid.UUID(_my_id(client, ben))
    chat_id = uuid.UUID(_start_chat(client, ana, "ben@example.com"))
    for body in ["one", "two", "three"]:
        _send(client, ana, chat_id, body)

    assert mark_delivered(db, chat_id, ben_id, 2) == 2
    assert mark_delivered(db, chat_id, ben_id, 1) is None  # backwards: ignored
    assert mark_delivered(db, chat_id, ben_id, 99) == 3  # capped at #3, the last message
    assert mark_delivered(db, chat_id, ben_id, 99) is None  # already there: nothing moves


def test_a_non_members_delivered_is_ignored(client, sign_up, db):
    ana, cara = sign_up("Ana"), sign_up("Cara")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    _send(client, ana, chat_id, "just for Ben")

    assert mark_delivered(db, uuid.UUID(chat_id), uuid.UUID(_my_id(client, cara)), 1) is None
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
