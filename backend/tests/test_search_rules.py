"""Search runs only on the device (D12, D40). The server's part is small: no
route that searches text, and the chat list's number that tells the app its
own copy has fallen behind."""

import uuid

from app.main import app

# Names a route would use if it searched text
SEARCH_WORDS = {"q", "query", "search", "term", "text", "keyword"}


def _chat_with_ben(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")
    response = client.post("/api/chats/direct", json={"email": "ben@example.com"}, headers=ana)
    assert response.status_code == 201
    return ana, response.json()["id"]


def _send(client, me, chat_id, body="hello") -> dict:
    response = client.post(
        f"/api/chats/{chat_id}/messages", json={"client_msg_id": str(uuid.uuid4()), "body": body}, headers=me
    )
    assert response.status_code == 201
    return response.json()


def _row(client, me, chat_id) -> dict:
    return next(row for row in client.get("/api/chats", headers=me).json() if row["id"] == chat_id)


def test_no_route_searches_text():
    # The app's own list of every route and its parameters
    paths = app.openapi()["paths"]
    assert "/api/chats/{chat_id}/messages" in paths  # it really is looking at the routes
    for path, operations in paths.items():
        assert "search" not in path.lower(), path
        for operation in operations.values():
            names = {param["name"].lower() for param in operation.get("parameters", []) if param["in"] == "query"}
            assert not names & SEARCH_WORDS, path


def test_last_seq_counts_changes_the_preview_skips(client, sign_up):
    ana, chat_id = _chat_with_ben(client, sign_up)
    assert _row(client, ana, chat_id)["last_seq"] == 0

    _send(client, ana, chat_id, "hello")
    response = client.patch(f"/api/chats/{chat_id}/messages/1", json={"body": "changed"}, headers=ana)
    assert response.status_code == 200

    row = _row(client, ana, chat_id)
    assert row["last_message"]["seq"] == 1  # the edit has no bubble
    assert row["last_seq"] == 2  # but the app must still fetch it


def test_last_seq_catches_up_to_a_change_made_while_away(client, sign_up):
    # What the app does when last_seq is ahead: ask for everything after its mark
    ana, chat_id = _chat_with_ben(client, sign_up)
    _send(client, ana, chat_id, "secret")
    my_mark = _row(client, ana, chat_id)["last_seq"]

    assert client.delete(f"/api/chats/{chat_id}/messages/1", headers=ana).status_code == 200

    assert _row(client, ana, chat_id)["last_seq"] > my_mark
    page = client.get(f"/api/chats/{chat_id}/messages?after={my_mark}", headers=ana).json()
    assert [row["kind"] for row in page["messages"]] == ["delete"]
    assert page["messages"][0]["target"]["deleted"] is True
    assert page["messages"][0]["target"]["body"] == ""


def test_last_seq_stops_where_i_left(client, sign_up):
    ana = sign_up("Ana")
    ben = sign_up("Ben")
    response = client.post(
        "/api/chats/groups", json={"name": "Trip", "emails": ["ben@example.com"], "user_ids": []}, headers=ana
    )
    assert response.status_code == 201
    chat_id = response.json()["id"]

    assert client.post(f"/api/chats/{chat_id}/leave", headers=ben).status_code == 200
    gone_at = _row(client, ben, chat_id)["last_seq"]
    _send(client, ana, chat_id, "after Ben left")

    assert _row(client, ben, chat_id)["last_seq"] == gone_at
    assert _row(client, ana, chat_id)["last_seq"] == gone_at + 1
