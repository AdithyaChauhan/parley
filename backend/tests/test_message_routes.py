import uuid


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


def _history(client, me, chat_id, query=""):
    return client.get(f"/api/chats/{chat_id}/messages{query}", headers=me)


def _seqs(page) -> list[int]:
    return [message["seq"] for message in page["messages"]]


def test_send_gives_201_and_a_resend_gives_200_with_the_first_copy(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    client_msg_id = uuid.uuid4()

    first = _send(client, ana, chat_id, "hi", client_msg_id)
    # The Wi-Fi blipped, so the app sends the same message again.
    resend = _send(client, ana, chat_id, "hi", client_msg_id)

    assert first.status_code == 201
    assert first.json()["seq"] == 1
    assert resend.status_code == 200
    assert resend.json() == first.json()
    assert _seqs(_history(client, ana, chat_id).json()) == [1]  # still only one copy


def test_body_is_trimmed_and_must_be_1_to_4000_letters(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")

    assert _send(client, ana, chat_id, "  hi  ").json()["body"] == "hi"
    assert _send(client, ana, chat_id, "x" * 4000).status_code == 201
    assert _send(client, ana, chat_id, "   ").status_code == 422
    assert _send(client, ana, chat_id, "x" * 4001).status_code == 422


def test_stranger_and_made_up_chat_get_the_same_404(client, sign_up):
    ana, cara = sign_up("Ana"), sign_up("Cara")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    made_up_id = uuid.uuid4()

    not_a_member = _send(client, cara, chat_id, "let me in")
    no_such_chat = _send(client, cara, made_up_id, "let me in")

    assert not_a_member.status_code == 404
    # The same reply, so Cara can't tell that chat_id is a real chat.
    assert not_a_member.json() == no_such_chat.json()
    assert _history(client, cara, chat_id).status_code == 404
    assert _history(client, cara, made_up_id).status_code == 404


def test_message_routes_need_a_login(client):
    chat_id = uuid.uuid4()

    assert client.get(f"/api/chats/{chat_id}/messages").status_code == 401
    assert client.post(
        f"/api/chats/{chat_id}/messages", json={"client_msg_id": str(uuid.uuid4()), "body": "hi"}
    ).status_code == 401


def test_scrolling_up_loads_30_at_a_time_by_number(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    for n in range(1, 71):
        _send(client, ana, chat_id, f"message {n}")

    newest = _history(client, ana, chat_id).json()
    older = _history(client, ana, chat_id, "?before=41").json()
    oldest = _history(client, ana, chat_id, "?before=11").json()

    assert _seqs(newest) == list(range(70, 40, -1))  # #70 ... #41
    assert newest["has_more"] is True
    assert _seqs(older) == list(range(40, 10, -1))  # #40 ... #11
    assert older["has_more"] is True
    assert _seqs(oldest) == list(range(10, 0, -1))  # #10 ... #1
    assert oldest["has_more"] is False


def test_limit_can_be_smaller_but_not_over_100(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    for n in range(3):
        _send(client, ana, chat_id, f"message {n}")

    assert _seqs(_history(client, ana, chat_id, "?limit=2").json()) == [3, 2]
    assert _history(client, ana, chat_id, "?limit=100").status_code == 200
    assert _history(client, ana, chat_id, "?limit=101").status_code == 422


def test_catching_up_returns_the_ones_after_oldest_first(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")
    for n in range(1, 6):
        _send(client, ana, chat_id, f"message {n}")

    # Ben's app had up to #1 when his line dropped. limit=2 keeps the pages small.
    first = _history(client, ben, chat_id, "?after=1&limit=2").json()
    second = _history(client, ben, chat_id, "?after=3&limit=2").json()
    nothing_new = _history(client, ben, chat_id, "?after=5").json()

    assert _seqs(first) == [2, 3]  # oldest first
    assert first["has_more"] is True  # ask again with after=3
    assert _seqs(second) == [4, 5]
    assert second["has_more"] is False
    assert _seqs(nothing_new) == []
    assert nothing_new["has_more"] is False
    # Everyone's bookmarks come too, so the ticks are right after a catch-up.
    assert len(first["members"]) == 2
    # after=0: an empty chat on screen gets everything from #1.
    assert _seqs(_history(client, ben, chat_id, "?after=0&limit=2").json()) == [1, 2]


def test_before_and_after_together_give_422(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")
    chat_id = _start_chat(client, ana, "ben@example.com")

    assert _history(client, ana, chat_id, "?before=5&after=2").status_code == 422
    assert _history(client, ana, chat_id, "?after=-1").status_code == 422


def test_two_person_story(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")

    # Ana starts a chat with Ben and sends 3 messages.
    chat_id = _start_chat(client, ana, "ben@example.com")
    for body in ["hey", "are you free", "at 6?"]:
        assert _send(client, ana, chat_id, body).status_code == 201

    # Ben sees them, newest first, numbered in order.
    page = _history(client, ben, chat_id).json()
    assert [m["body"] for m in page["messages"]] == ["at 6?", "are you free", "hey"]
    assert _seqs(page) == [3, 2, 1]
    assert page["has_more"] is False

    # Ben's chat list shows 3 unread. Ana's shows none: she wrote them.
    [bens_row] = client.get("/api/chats", headers=ben).json()
    assert bens_row["name"] == "Ana"
    assert bens_row["unread"] == 3
    assert bens_row["last_message"]["preview"] == "at 6?"
    assert client.get("/api/chats", headers=ana).json()[0]["unread"] == 0

    # Cara isn't in the chat: she can't read it or send to it.
    assert _history(client, cara, chat_id).status_code == 404
    assert _send(client, cara, chat_id, "hi").status_code == 404
    assert client.get("/api/chats", headers=cara).json() == []
