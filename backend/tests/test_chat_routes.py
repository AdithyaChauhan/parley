import uuid

from app.chats import service


def _start_chat(client, me, email):
    return client.post("/api/chats/direct", json={"email": email}, headers=me)


def _send(client, me, chat_id, body):
    response = client.post(
        f"/api/chats/{chat_id}/messages",
        json={"client_msg_id": str(uuid.uuid4()), "body": body},
        headers=me,
    )
    assert response.status_code == 201


def test_start_chat_gives_201_then_200_with_the_same_chat(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")

    first = _start_chat(client, ana, "ben@example.com")
    again = _start_chat(client, ana, "ben@example.com")
    from_ben = _start_chat(client, ben, "ana@example.com")

    assert first.status_code == 201
    assert first.json()["name"] == "Ben"
    assert again.status_code == 200
    assert from_ben.status_code == 200
    # Whoever starts it, the two of them have one chat.
    assert again.json()["id"] == from_ben.json()["id"] == first.json()["id"]


def test_own_email_gives_400_and_unknown_email_gives_404(client, sign_up):
    ana = sign_up("Ana")

    assert _start_chat(client, ana, "ana@example.com").status_code == 400
    assert _start_chat(client, ana, "nobody@example.com").status_code == 404


def test_chat_routes_need_a_login(client):
    assert client.post("/api/chats/direct", json={"email": "ben@example.com"}).status_code == 401
    assert client.get("/api/chats").status_code == 401


def test_two_start_chats_at_once_still_give_one_chat(client, sign_up, monkeypatch):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com").json()["id"]

    # Two clicks at the same moment both look, both find nothing, and both try
    # to save. Fake that: make the first look miss, as if the other click's
    # chat wasn't saved yet. Our save is then refused by the UNIQUE direct_key.
    find_direct_chat = service._find_direct_chat
    looks = []

    def miss_the_first_look(db, key):
        looks.append(key)
        return None if len(looks) == 1 else find_direct_chat(db, key)

    monkeypatch.setattr(service, "_find_direct_chat", miss_the_first_look)

    response = _start_chat(client, ben, "ana@example.com")

    assert response.status_code == 200
    assert response.json()["id"] == chat_id
    assert len(looks) == 2  # it really missed, was refused, and looked again
    assert len(client.get("/api/chats", headers=ben).json()) == 1


def test_both_people_see_the_chat_under_the_other_ones_name(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    _start_chat(client, ana, "ben@example.com")

    [anas_row] = client.get("/api/chats", headers=ana).json()
    [bens_row] = client.get("/api/chats", headers=ben).json()

    assert anas_row["name"] == "Ben"
    assert bens_row["name"] == "Ana"
    assert anas_row["id"] == bens_row["id"]
    assert anas_row["kind"] == "direct"
    # No messages yet.
    assert anas_row["last_message"] is None
    assert anas_row["unread"] == 0


def test_chat_list_shows_newest_activity_first(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")
    sign_up("Cara")
    with_ben = _start_chat(client, ana, "ben@example.com").json()["id"]
    _start_chat(client, ana, "cara@example.com")

    # The Cara chat is newer, until a message arrives in the Ben chat.
    assert [row["name"] for row in client.get("/api/chats", headers=ana).json()] == ["Cara", "Ben"]
    _send(client, ana, with_ben, "hi Ben")
    assert [row["name"] for row in client.get("/api/chats", headers=ana).json()] == ["Ben", "Cara"]


def test_chat_list_shows_the_last_message_and_unread(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com").json()["id"]
    _send(client, ana, chat_id, "first")
    _send(client, ana, chat_id, "x" * 150)

    [anas_row] = client.get("/api/chats", headers=ana).json()
    [bens_row] = client.get("/api/chats", headers=ben).json()

    assert bens_row["last_message"]["seq"] == 2
    assert bens_row["last_message"]["preview"] == "x" * 100  # only the start of the text
    assert bens_row["unread"] == 2
    assert anas_row["unread"] == 0  # your own messages are never unread
