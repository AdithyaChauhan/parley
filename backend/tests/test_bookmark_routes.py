import uuid
from contextlib import contextmanager


def _start_chat(client, me, email) -> str:
    response = client.post("/api/chats/direct", json={"email": email}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _send(client, me, chat_id):
    response = client.post(
        f"/api/chats/{chat_id}/messages",
        json={"client_msg_id": str(uuid.uuid4()), "body": "hi"},
        headers=me,
    )
    assert response.status_code == 201
    return response.json()


def _door(client, me, chat_id, kind, seq):
    """POST /api/chats/<id>/delivered or /read, the HTTP door (D20)."""
    return client.post(f"/api/chats/{chat_id}/{kind}", json={"seq": seq}, headers=me)


def _bookmarks(response) -> tuple[int, int]:
    assert response.status_code == 200
    body = response.json()
    return body["delivered_up_to"], body["read_up_to"]


@contextmanager
def _open_line(client, me):
    """One open tab: get a ticket, open the line, read the hello."""
    ticket = client.post("/api/live/ticket", headers=me).json()["ticket"]
    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"
        yield line


def _chat_with_three_messages(client, sign_up):
    """Ana sends #1, #2, #3 to Ben. Returns (ana, ben, chat_id)."""
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    for _ in range(3):
        _send(client, ana, chat_id)
    return ana, ben, chat_id


def test_delivered_moves_forward_only_and_never_past_the_last_message(client, sign_up):
    _, ben, chat_id = _chat_with_three_messages(client, sign_up)

    assert _bookmarks(_door(client, ben, chat_id, "delivered", 2)) == (2, 0)
    assert _bookmarks(_door(client, ben, chat_id, "delivered", 1)) == (2, 0)  # never backwards
    assert _bookmarks(_door(client, ben, chat_id, "delivered", 99)) == (3, 0)  # stops at #3


def test_read_moves_forward_only_and_lifts_delivered(client, sign_up):
    _, ben, chat_id = _chat_with_three_messages(client, sign_up)

    assert _bookmarks(_door(client, ben, chat_id, "read", 2)) == (2, 2)  # read lifts delivered
    assert _bookmarks(_door(client, ben, chat_id, "read", 1)) == (2, 2)  # never backwards
    assert _bookmarks(_door(client, ben, chat_id, "read", 99)) == (3, 3)  # stops at #3


def test_a_non_member_or_unknown_chat_gets_404(client, sign_up):
    _, _, chat_id = _chat_with_three_messages(client, sign_up)
    cy = sign_up("Cy")

    # The same 404 for "not your chat" and "no such chat".
    assert _door(client, cy, chat_id, "read", 1).status_code == 404
    assert _door(client, cy, uuid.uuid4(), "delivered", 1).status_code == 404


def test_seq_must_be_at_least_1(client, sign_up):
    _, ben, chat_id = _chat_with_three_messages(client, sign_up)

    assert _door(client, ben, chat_id, "read", 0).status_code == 422


def test_after_an_http_read_the_chat_list_shows_unread_0(client, sign_up):
    _, ben, chat_id = _chat_with_three_messages(client, sign_up)
    assert client.get("/api/chats", headers=ben).json()[0]["unread"] == 3

    _door(client, ben, chat_id, "read", 3)

    assert client.get("/api/chats", headers=ben).json()[0]["unread"] == 0


def test_an_http_read_pushes_a_receipt_but_one_that_doesnt_move_pushes_nothing(client, sign_up):
    ana, ben, chat_id = _chat_with_three_messages(client, sign_up)

    with _open_line(client, ana) as anas_line:
        _door(client, ben, chat_id, "read", 2)
        receipt = anas_line.receive_json()
        assert receipt["type"] == "receipt"
        assert receipt["data"]["read_up_to"] == 2

        _door(client, ben, chat_id, "read", 2)  # already there: nothing moves
        # A test can't wait for "nothing", so: the next push must be Ben's
        # message, not a second receipt.
        _send(client, ben, chat_id)
        assert anas_line.receive_json()["type"] == "message.new"


def test_a_live_read_that_doesnt_move_pushes_nothing_either(client, sign_up):
    # The other door, the live line: the same function, so the same rule (D20).
    ana, ben, chat_id = _chat_with_three_messages(client, sign_up)

    with _open_line(client, ana) as anas_line, _open_line(client, ben) as bens_line:
        anas_line.receive_json()  # Ben came online
        bens_line.send_json({"type": "read", "data": {"chat_id": chat_id, "seq": 2}})
        assert anas_line.receive_json()["type"] == "receipt"

        bens_line.send_json({"type": "read", "data": {"chat_id": chat_id, "seq": 2}})
        _send(client, ben, chat_id)
        assert anas_line.receive_json()["type"] == "message.new"
