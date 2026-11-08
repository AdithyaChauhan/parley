import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text

from app.auth.models import User
from app.config import settings
from app.db import SessionLocal
from app.groups import service
from app.notify import queues, worker


def _my_id(client, me) -> str:
    return client.get("/api/auth/me", headers=me).json()["id"]


def _start_chat(client, me, email) -> str:
    response = client.post("/api/chats/direct", json={"email": email}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _create(client, me, name="Trip", emails=(), user_ids=()):
    return client.post(
        "/api/chats/groups",
        json={"name": name, "emails": list(emails), "user_ids": [str(u) for u in user_ids]},
        headers=me,
    )


def _group(client, me, *names) -> str:
    """A group made by me, with these people (by email). Returns its id."""
    response = _create(client, me, emails=[f"{n.lower()}@example.com" for n in names])
    assert response.status_code == 201
    return response.json()["id"]


def _send(client, me, chat_id, body="hi"):
    return client.post(
        f"/api/chats/{chat_id}/messages",
        json={"client_msg_id": str(uuid.uuid4()), "body": body},
        headers=me,
    )


def _history(client, me, chat_id, query=""):
    return client.get(f"/api/chats/{chat_id}/messages{query}", headers=me)


def _seqs(page) -> list[int]:
    return [message["seq"] for message in page["messages"]]


def _events(page) -> list[str]:
    return [m["data"]["event"] if m["kind"] == "system" else m["body"] for m in page["messages"]]


def _add(client, me, chat_id, *names):
    return client.post(
        f"/api/chats/{chat_id}/members",
        json={"emails": [f"{n.lower()}@example.com" for n in names]},
        headers=me,
    )


def _remove(client, me, chat_id, user_id):
    return client.delete(f"/api/chats/{chat_id}/members/{user_id}", headers=me)


def _members(client, me, chat_id) -> dict[str, str]:
    """Current members: name -> role."""
    response = client.get(f"/api/chats/{chat_id}/members", headers=me)
    assert response.status_code == 200
    return {member["name"]: member["role"] for member in response.json()}


def _row(client, me, chat_id) -> dict:
    return next(chat for chat in client.get("/api/chats", headers=me).json() if chat["id"] == chat_id)


@contextmanager
def _open_line(client, me):
    """One open tab: get a ticket, open the line, read the hello."""
    ticket = client.post("/api/live/ticket", headers=me).json()["ticket"]
    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"
        yield line


def _jobs_in(channel, box) -> list[dict]:
    jobs = []
    while True:
        method, _properties, body = channel.basic_get(box, auto_ack=True)
        if method is None:
            return jobs
        jobs.append(json.loads(body))


# --- Creating ---


def test_create_makes_me_admin_and_the_created_note_is_number_1(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    sign_up("Cara")

    response = _create(client, ana, "  Trip  ", emails=["ben@example.com", "CARA@example.com"])

    assert response.status_code == 201
    row = response.json()
    assert (row["kind"], row["name"], row["role"], row["left"]) == ("group", "Trip", "admin", False)
    assert row["last_message"]["kind"] == "system"
    assert row["last_message"]["data"]["event"] == "created"
    assert _members(client, ana, row["id"]) == {"Ana": "admin", "Ben": "member", "Cara": "member"}
    # Ben sees it too, with the note as #1, and it counts as unread for him.
    page = _history(client, ben, row["id"]).json()
    assert _seqs(page) == [1]
    assert page["messages"][0]["sender_name"] == "Ana"
    assert _row(client, ben, row["id"])["unread"] == 1


def test_name_must_be_1_to_50_letters(client, sign_up):
    ana = sign_up("Ana")
    sign_up("Ben")

    assert _create(client, ana, "   ", emails=["ben@example.com"]).status_code == 422
    assert _create(client, ana, "x" * 51, emails=["ben@example.com"]).status_code == 422
    assert _create(client, ana, "x" * 50, emails=["ben@example.com"]).status_code == 201


def test_people_come_from_my_direct_chats_or_an_exact_email(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    sign_up("Cara")
    ben_id, cara_id = _my_id(client, ben), _my_id(client, sign_up("Dev"))
    _start_chat(client, ana, "ben@example.com")

    # Ben: Ana has a direct chat with him. Dev: she doesn't, so his id alone isn't enough.
    assert _create(client, ana, user_ids=[ben_id]).status_code == 201
    assert _create(client, ana, user_ids=[cara_id]).status_code == 400
    assert _create(client, ana, emails=["nobody@example.com"]).status_code == 404
    # Adding myself, or the same person twice, is ignored.
    chat_id = _create(client, ana, user_ids=[ben_id], emails=["ana@example.com", "ben@example.com"]).json()["id"]
    assert _members(client, ana, chat_id) == {"Ana": "admin", "Ben": "member"}


@pytest.fixture
def no_limits(monkeypatch):
    """Rate limits off for one test, as in the load test (D33): these tests
    look up dozens of emails, past start-chat's 20 a minute."""
    monkeypatch.setattr(settings, "rate_limits_enabled", False)


def _many_people(db, count):
    """People made straight in the database: signing up this many would hit the sign-up limit."""
    for n in range(count):
        db.add(User(email=f"p{n}@example.com", name=f"P{n}", password_hash="x"))
    db.commit()
    return [f"p{n}@example.com" for n in range(count)]


def test_a_group_has_at_most_50_members(client, sign_up, db, no_limits):
    ana = sign_up("Ana")
    emails = _many_people(db, 50)

    assert _create(client, ana, "Big", emails=emails).status_code == 400  # 51 with Ana
    chat_id = _create(client, ana, "Big", emails=emails[:49]).json()["id"]  # exactly 50
    assert _add(client, ana, chat_id, "P49").status_code == 400
    assert len(_members(client, ana, chat_id)) == 50


# --- Roles ---


def test_only_admins_add_remove_rename_and_make_admin(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    cara_id = _my_id(client, sign_up("Cara"))
    sign_up("Dev")
    chat_id = _group(client, ana, "Ben", "Cara")

    assert _add(client, ben, chat_id, "Dev").status_code == 403
    assert _remove(client, ben, chat_id, cara_id).status_code == 403
    assert client.patch(f"/api/chats/{chat_id}", json={"name": "Mine"}, headers=ben).status_code == 403
    assert client.post(f"/api/chats/{chat_id}/members/{cara_id}/admin", headers=ben).status_code == 403

    # Once Ana makes him admin, he can.
    assert client.post(f"/api/chats/{chat_id}/members/{_my_id(client, ben)}/admin", headers=ana).status_code == 200
    assert _add(client, ben, chat_id, "Dev").status_code == 200
    renamed = client.patch(f"/api/chats/{chat_id}", json={"name": "Mine"}, headers=ben)
    assert renamed.json()["name"] == "Mine"
    assert _row(client, ana, chat_id)["name"] == "Mine"
    assert _events(_history(client, ana, chat_id).json())[::-1] == ["created", "made_admin", "added", "renamed"]


def test_strangers_and_direct_chats_get_404(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    chat_id = _group(client, ana, "Ben")
    direct = _start_chat(client, ana, "cara@example.com")

    assert client.get(f"/api/chats/{chat_id}/members", headers=cara).status_code == 404
    assert _send(client, cara, chat_id).status_code == 404
    assert _add(client, ana, direct, "Ben").status_code == 404
    assert client.post(f"/api/chats/{direct}/leave", headers=ana).status_code == 404
    assert client.get(f"/api/chats/{uuid.uuid4()}/members", headers=ben).status_code == 404


def test_the_last_admin_leaving_makes_the_longest_standing_member_admin(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    sign_up("Dev")
    chat_id = _group(client, ana, "Cara")  # Cara is in from #1
    _add(client, ana, chat_id, "Ben", "Dev")  # Ben and Dev from #2

    left = client.post(f"/api/chats/{chat_id}/leave", headers=ana)

    assert left.status_code == 200
    assert left.json()["left"] is True
    assert _members(client, ben, chat_id) == {"Cara": "admin", "Ben": "member", "Dev": "member"}
    note = _history(client, cara, chat_id).json()["messages"][0]
    assert note["data"]["event"] == "left"
    assert note["data"]["new_admin"]["name"] == "Cara"
    # Another admin still there: nobody is promoted.
    client.post(f"/api/chats/{chat_id}/members/{_my_id(client, ben)}/admin", headers=cara)
    client.post(f"/api/chats/{chat_id}/leave", headers=cara)
    assert _members(client, ben, chat_id) == {"Ben": "admin", "Dev": "member"}


def test_the_last_person_can_leave_an_empty_group(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _group(client, ana, "Ben")

    assert client.post(f"/api/chats/{chat_id}/leave", headers=ben).status_code == 200
    assert client.post(f"/api/chats/{chat_id}/leave", headers=ana).status_code == 200
    assert client.post(f"/api/chats/{chat_id}/leave", headers=ana).status_code == 403  # already gone


# --- Membership has a start and an end ---


def test_a_new_member_sees_from_when_they_joined(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    sign_up("Cara")
    chat_id = _group(client, ana, "Cara")
    _send(client, ana, chat_id, "before Ben")  # #2

    _add(client, ana, chat_id, "Ben")  # #3
    _send(client, ana, chat_id, "after Ben")  # #4

    page = _history(client, ben, chat_id).json()
    assert _seqs(page) == [4, 3]
    assert _events(page) == ["after Ben", "added"]
    # Asking for older ones, or catching up from 0, gives nothing before #3 either.
    assert _seqs(_history(client, ben, chat_id, "?before=3").json()) == []
    assert _seqs(_history(client, ben, chat_id, "?after=0").json()) == [3, 4]
    # His unread counts from his start, not from #1.
    assert _row(client, ben, chat_id)["unread"] == 2


def test_a_removed_member_cant_read_new_messages_or_send(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    sign_up("Cara")
    ben_id = _my_id(client, ben)
    chat_id = _group(client, ana, "Ben", "Cara")
    _send(client, ben, chat_id, "mine")  # #2

    assert _remove(client, ana, chat_id, ben_id).status_code == 200  # #3
    _send(client, ana, chat_id, "secret")  # #4

    # He keeps what he had, up to the note that removed him, and nothing after.
    page = _history(client, ben, chat_id).json()
    assert _seqs(page) == [3, 2, 1]
    assert _seqs(_history(client, ben, chat_id, "?after=3").json()) == []
    sent = _send(client, ben, chat_id, "let me back")
    assert sent.status_code == 403
    assert _seqs(_history(client, ana, chat_id).json())[0] == 4  # nothing was saved
    # The chat stays in his list, read-only, ending at the note.
    row = _row(client, ben, chat_id)
    assert row["left"] is True
    assert row["last_message"]["seq"] == 3
    assert row["last_message"]["data"]["event"] == "removed"
    # He can't see who's in it now, or type in it.
    assert client.get(f"/api/chats/{chat_id}/members", headers=ben).status_code == 403
    # A read past his end stops at it.
    assert client.post(f"/api/chats/{chat_id}/read", json={"seq": 99}, headers=ben).json()["read_up_to"] == 3


def test_a_removed_member_gets_the_note_live_but_nothing_after(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    sign_up("Cara")
    ben_id = _my_id(client, ben)
    chat_id = _group(client, ana, "Ben", "Cara")
    direct = _start_chat(client, ana, "ben@example.com")

    with _open_line(client, ben) as bens_line:
        _remove(client, ana, chat_id, ben_id)
        note = bens_line.receive_json()
        assert note["type"] == "message.new"
        assert note["data"]["data"]["event"] == "removed"

        _send(client, ana, chat_id, "not for Ben")
        # His next event is Ana's direct message, not the group's.
        _send(client, ana, direct, "hi Ben")
        assert bens_line.receive_json()["data"]["body"] == "hi Ben"


def test_typing_from_someone_who_left_goes_nowhere(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    sign_up("Cara")
    chat_id = _group(client, ana, "Ben", "Cara")
    client.post(f"/api/chats/{chat_id}/leave", headers=ben)

    with _open_line(client, ana) as anas_line, _open_line(client, ben) as bens_line:
        bens_line.send_json({"type": "typing", "data": {"chat_id": chat_id}})
        # Ana's next event is Cara's message, not Ben's typing.
        _send(client, ana, chat_id, "still here")
        assert anas_line.receive_json()["type"] == "message.new"


def test_a_removed_member_gets_no_notification_jobs(client, sign_up, rabbit):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    ben_id, cara_id = _my_id(client, ben), _my_id(client, cara)
    chat_id = _group(client, ana, "Ben", "Cara")
    # Group notes don't notify: only real messages do.
    assert _jobs_in(rabbit, queues.WAIT) == []

    _remove(client, ana, chat_id, ben_id)
    _send(client, ana, chat_id, "hi all")

    jobs = _jobs_in(rabbit, queues.WAIT)
    assert [job["recipient_id"] for job in jobs] == [cara_id]


def test_a_job_made_before_the_removal_is_skipped_by_the_worker(client, sign_up, rabbit):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    sign_up("Cara")
    ben_id = _my_id(client, ben)
    chat_id = _group(client, ana, "Ben", "Cara")
    sent = _send(client, ana, chat_id, "hi").json()
    job = queues.Job(uuid.UUID(sent["id"]), uuid.UUID(chat_id), sent["seq"], uuid.UUID(ben_id))

    _remove(client, ana, chat_id, ben_id)

    assert worker.handle(job, attempt=1) == "skip: message or member gone"


def test_a_group_notification_is_titled_sender_in_group(client, sign_up, monkeypatch):
    ana, cara = sign_up("Ana"), sign_up("Cara")
    cara_id = _my_id(client, cara)
    chat_id = _group(client, ana, "Cara")
    sent = _send(client, ana, chat_id, "hi").json()
    titles = []
    monkeypatch.setattr(worker.notifier, "send", lambda job, name, title: titles.append(title) or "sent")

    worker.handle(queues.Job(uuid.UUID(sent["id"]), uuid.UUID(chat_id), sent["seq"], uuid.UUID(cara_id)), 1)

    assert titles == ["Ana in Trip"]


def test_rejoining_starts_again_from_the_new_add(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = _my_id(client, ben)
    chat_id = _group(client, ana, "Ben")
    _remove(client, ana, chat_id, ben_id)  # #2
    _send(client, ana, chat_id, "while he was out")  # #3

    _add(client, ana, chat_id, "Ben")  # #4

    assert _row(client, ben, chat_id)["left"] is False
    assert _seqs(_history(client, ben, chat_id).json()) == [4]
    assert _send(client, ben, chat_id, "back").status_code == 201


# --- Fan-out and ticks ---


def test_one_message_reaches_every_current_member_live(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    chat_id = _group(client, ana, "Ben", "Cara")

    with _open_line(client, ben) as bens_line, _open_line(client, cara) as caras_line:
        sent = _send(client, ana, chat_id, "hi all").json()

        assert bens_line.receive_json() == {"type": "message.new", "data": sent}
        assert caras_line.receive_json() == {"type": "message.new", "data": sent}
    assert sent["sender_name"] == "Ana"


def test_group_ticks_use_the_lowest_bookmark_of_the_current_members(client, sign_up):
    """The app draws ticks from the page's members: grey once every other
    current member has it, teal once every other one has read it (D37)."""
    ana, ben, cara, dev = sign_up("Ana"), sign_up("Ben"), sign_up("Cara"), sign_up("Dev")
    ana_id, cara_id = _my_id(client, ana), _my_id(client, cara)
    chat_id = _group(client, ana, "Ben", "Cara")
    _send(client, ana, chat_id, "one")  # #2

    def ticks(seq):
        members = [m for m in _history(client, ana, chat_id).json()["members"] if m["user_id"] != ana_id]
        if seq <= min(m["read_up_to"] for m in members):
            return "read"
        if seq <= min(m["delivered_up_to"] for m in members):
            return "delivered"
        return "sent"

    client.post(f"/api/chats/{chat_id}/read", json={"seq": 2}, headers=ben)
    assert ticks(2) == "sent"  # Cara doesn't have it yet
    client.post(f"/api/chats/{chat_id}/delivered", json={"seq": 2}, headers=cara)
    assert ticks(2) == "delivered"
    # Dev joins at #3: his low bookmarks (2) never hold back #2, which he can't see.
    _add(client, ana, chat_id, "Dev")
    assert ticks(2) == "delivered"
    client.post(f"/api/chats/{chat_id}/read", json={"seq": 2}, headers=cara)
    assert ticks(2) == "read"
    # Cara never reads #4, but once she's removed, only Ben and Dev count.
    _send(client, ana, chat_id, "two")  # #4
    for person in (ben, dev):
        client.post(f"/api/chats/{chat_id}/read", json={"seq": 4}, headers=person)
    assert ticks(4) == "sent"
    _remove(client, ana, chat_id, cara_id)
    assert ticks(4) == "read"


def _group_receipt(chat_id, delivered, read) -> dict:
    return {"type": "group_receipt", "data": {"chat_id": chat_id, "delivered_up_to": delivered, "read_up_to": read}}


def test_a_group_read_goes_to_my_own_tabs_and_the_others_get_only_the_lowest(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    ben_id = _my_id(client, ben)
    chat_id = _group(client, ana, "Ben", "Cara")
    _send(client, ana, chat_id, "one")  # #2

    with _open_line(client, ana) as anas_line, _open_line(client, ben) as bens_line:
        client.post(f"/api/chats/{chat_id}/read", json={"seq": 2}, headers=ben)
        # Ben's own tabs hear his read (for his unread badge). Cara hasn't read
        # #2, so the group's lowest didn't move, and Ana hears nothing.
        assert bens_line.receive_json() == {
            "type": "receipt",
            "data": {"chat_id": chat_id, "user_id": ben_id, "delivered_up_to": 2, "read_up_to": 2},
        }
        client.post(f"/api/chats/{chat_id}/read", json={"seq": 2}, headers=cara)
        # Cara was the last: the lowest moves to #2, and everyone hears it once.
        # Ana's first event is this one, so Ben's own receipt never reached her.
        assert anas_line.receive_json() == _group_receipt(chat_id, 2, 2)
        assert bens_line.receive_json() == _group_receipt(chat_id, 2, 2)


def test_a_send_or_a_removal_can_lift_the_group_lowest(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    cara_id = _my_id(client, cara)
    chat_id = _group(client, ana, "Ben", "Cara")  # #1
    _send(client, ana, chat_id, "one")  # #2
    client.post(f"/api/chats/{chat_id}/read", json={"seq": 2}, headers=cara)

    with _open_line(client, ana) as anas_line:
        # Ben never read #2, but sending counts as reading (D20): his #3 lifts
        # the lowest to #2 (Ana and Cara are at 2).
        _send(client, ben, chat_id, "late")  # #3
        # Ana reads #3, but Cara still holds the lowest at #2: only Ana's own tabs hear it.
        client.post(f"/api/chats/{chat_id}/read", json={"seq": 3}, headers=ana)
        assert anas_line.receive_json()["type"] == "message.new"
        assert anas_line.receive_json() == _group_receipt(chat_id, 2, 2)
        assert anas_line.receive_json()["type"] == "receipt"

        # Cara is removed: only Ana (#4, the note) and Ben (#3) count now.
        _remove(client, ana, chat_id, cara_id)
        assert anas_line.receive_json()["data"]["data"]["event"] == "removed"
        assert anas_line.receive_json() == _group_receipt(chat_id, 3, 3)


def _ben_goes(client, ana, ben, chat_id, how):
    """Ben stops being a member: removed by Ana, or he leaves."""
    if how == "removed":
        response = _remove(client, ana, chat_id, _my_id(client, ben))
    else:
        response = client.post(f"/api/chats/{chat_id}/leave", headers=ben)
    assert response.status_code == 200


@pytest.mark.parametrize("how", ["removed", "left"])
def test_ben_going_turns_the_ticks_teal_when_everyone_left_has_read(client, sign_up, how):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    chat_id = _group(client, ana, "Ben", "Cara")  # #1
    _send(client, ana, chat_id, "hi")  # #2
    # Cara has read #2. Ben hasn't even got it.
    client.post(f"/api/chats/{chat_id}/read", json={"seq": 2}, headers=cara)

    with _open_line(client, ana) as anas_line, _open_line(client, cara) as caras_line:
        _ben_goes(client, ana, ben, chat_id, how)  # the note is #3
        # Nobody read anything, but only Ana and Cara count now, and both have
        # read #2: everyone still in the group hears it, and Ana's ticks turn teal.
        for line in (anas_line, caras_line):
            assert line.receive_json()["data"]["data"]["event"] == how
            assert line.receive_json() == _group_receipt(chat_id, 2, 2)


@pytest.mark.parametrize("how", ["removed", "left"])
def test_ben_going_keeps_the_ticks_grey_until_the_rest_have_read(client, sign_up, how):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    chat_id = _group(client, ana, "Ben", "Cara")  # #1
    _send(client, ana, chat_id, "hi")  # #2
    # Cara's device has #2, but she hasn't opened the chat.
    client.post(f"/api/chats/{chat_id}/delivered", json={"seq": 2}, headers=cara)

    with _open_line(client, ana) as anas_line:
        _ben_goes(client, ana, ben, chat_id, how)
        assert anas_line.receive_json()["data"]["data"]["event"] == how
        # Grey: delivered to everyone left, but Cara hasn't read #2.
        receipt = anas_line.receive_json()
        assert receipt["type"] == "group_receipt"
        assert receipt["data"]["delivered_up_to"] >= 2
        assert receipt["data"]["read_up_to"] < 2

        # Cara reads it: now it's teal.
        client.post(f"/api/chats/{chat_id}/read", json={"seq": 2}, headers=cara)
        assert anas_line.receive_json() == _group_receipt(chat_id, 2, 2)


def test_system_messages_keep_the_numbers_gap_free(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    ben_id = _my_id(client, ben)
    sign_up("Cara")
    chat_id = _group(client, ana, "Ben")

    # Changes and messages mixed, from two people, some refused.
    _send(client, ben, chat_id, "a")
    _add(client, ana, chat_id, "Cara")
    _add(client, ben, chat_id, "Cara")  # refused: Ben isn't admin
    client.patch(f"/api/chats/{chat_id}", json={"name": "Trip 2"}, headers=ana)
    client.patch(f"/api/chats/{chat_id}", json={"name": "Trip 2"}, headers=ana)  # no change, no note
    _send(client, ana, chat_id, "b")
    _remove(client, ana, chat_id, ben_id)
    _send(client, ben, chat_id, "refused")  # refused: Ben was removed
    _send(client, ana, chat_id, "c")

    seqs = _seqs(_history(client, ana, chat_id, "?after=0").json())
    assert seqs == list(range(1, 8))
    row = _row(client, ana, chat_id)
    assert row["last_message"]["seq"] == 7


def test_presence_news_goes_only_to_direct_chat_partners(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    _group(client, ana, "Ben")  # Ana and Ben share only a group
    direct = _start_chat(client, ana, "cara@example.com")

    with _open_line(client, ana) as anas_line:
        with _open_line(client, ben):
            pass
        # Ben came and went, but Ana hears nothing: the next event is a message.
        _send(client, cara, direct, "hi")
        assert anas_line.receive_json()["type"] == "message.new"


# --- Two admins at the same moment ---


def _user(db, name) -> User:
    return db.scalar(select(User).where(User.name == name))


def test_two_admins_removing_each_other_at_once_only_one_wins(client, sign_up):
    """Ana and Ben, both admins, remove each other at the same moment. Ana's
    change holds the group's lock; Ben's waits, then sees he was removed."""
    ana, ben = sign_up("Ana"), sign_up("Ben")
    sign_up("Cara")
    chat_id = uuid.UUID(_group(client, ana, "Ben", "Cara"))
    client.post(f"/api/chats/{chat_id}/members/{_my_id(client, ben)}/admin", headers=ana)

    with SessionLocal() as anas_db, SessionLocal() as bens_db:
        ana_user, ben_user = _user(anas_db, "Ana"), _user(bens_db, "Ben")
        # Ana's change starts first and holds the lock...
        service._lock_group(anas_db, chat_id)
        bens_result = {}

        def ben_removes_ana():
            try:
                service.remove_member(bens_db, chat_id, ben_user, ana_user.id)
                bens_result["outcome"] = "removed Ana"
            except HTTPException as error:
                bens_db.rollback()
                bens_result["outcome"] = error.status_code

        bens_try = threading.Thread(target=ben_removes_ana)
        bens_try.start()
        # ...so Ben's is waiting for it in PostgreSQL.
        _wait_for_a_lock_wait()
        service.remove_member(anas_db, chat_id, ana_user, ben_user.id)
        bens_try.join(timeout=10)

    assert bens_result["outcome"] == 403  # he's no longer a member
    assert _members(client, ana, chat_id) == {"Ana": "admin", "Cara": "member"}
    assert _seqs(_history(client, ana, chat_id, "?after=0").json()) == [1, 2, 3]


def _wait_for_a_lock_wait(seconds=5):
    """Until some session in the test database is waiting for a row lock."""
    deadline = time.monotonic() + seconds
    with SessionLocal() as db:
        while time.monotonic() < deadline:
            waiting = db.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity"
                    " WHERE datname = current_database() AND wait_event_type = 'Lock'"
                )
            )
            if waiting:
                return
            db.rollback()
            time.sleep(0.05)
    pytest.fail("nobody waited for the lock")


def test_two_admins_adding_at_once_never_pass_50_or_skip_a_number(client, sign_up, db, no_limits):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    emails = _many_people(db, 60)
    # Ana, Ben and 46 others: 48 members, room for 2 more.
    chat_id = _create(client, ana, emails=["ben@example.com"] + emails[:46]).json()["id"]
    client.post(f"/api/chats/{chat_id}/members/{_my_id(client, ben)}/admin", headers=ana)

    def add(who, first):
        people = {"emails": emails[first : first + 2]}
        return client.post(f"/api/chats/{chat_id}/members", json=people, headers=who).status_code

    # Ten adds of 2 different people at once, from both admins.
    with ThreadPoolExecutor(max_workers=6) as pool:
        codes = list(pool.map(lambda i: add(ana if i % 2 else ben, 46 + i), range(10)))

    assert len(_members(client, ana, chat_id)) == 50  # full, never over
    assert codes.count(200) >= 1 and set(codes) <= {200, 400}
    seqs = _seqs(_history(client, ana, chat_id, "?after=0&limit=100").json())
    assert seqs == list(range(1, len(seqs) + 1))
