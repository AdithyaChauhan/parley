"""Reactions, edit and delete for everyone (D39)."""

import urllib.request
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text, update

from app.db import SessionLocal
from app.files import cleanup
from app.files.models import Upload
from app.files.s3 import StoreError
from app.files.store import store
from app.messages.models import Message, Reaction
from app.notify import worker
from app.notify.queues import Job

THUMBS, HEART, LAUGH = "👍", "❤️", "😂"


def _my_id(client, me) -> str:
    return client.get("/api/auth/me", headers=me).json()["id"]


def _start_chat(client, me, email) -> str:
    response = client.post("/api/chats/direct", json={"email": email}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _group(client, me, *names) -> str:
    emails = [f"{n.lower()}@example.com" for n in names]
    response = client.post("/api/chats/groups", json={"name": "Trip", "emails": emails, "user_ids": []}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _send(client, me, chat_id, body="hello") -> dict:
    response = client.post(
        f"/api/chats/{chat_id}/messages", json={"client_msg_id": str(uuid.uuid4()), "body": body}, headers=me
    )
    assert response.status_code == 201
    return response.json()


def _react(client, me, chat_id, seq, emoji=THUMBS):
    return client.put(f"/api/chats/{chat_id}/messages/{seq}/reaction", json={"emoji": emoji}, headers=me)


def _unreact(client, me, chat_id, seq):
    return client.delete(f"/api/chats/{chat_id}/messages/{seq}/reaction", headers=me)


def _edit(client, me, chat_id, seq, body="changed"):
    return client.patch(f"/api/chats/{chat_id}/messages/{seq}", json={"body": body}, headers=me)


def _delete(client, me, chat_id, seq):
    return client.delete(f"/api/chats/{chat_id}/messages/{seq}", headers=me)


def _history(client, me, chat_id, query="") -> dict:
    response = client.get(f"/api/chats/{chat_id}/messages{query}", headers=me)
    assert response.status_code == 200
    return response.json()


def _row(client, me, chat_id) -> dict:
    return next(chat for chat in client.get("/api/chats", headers=me).json() if chat["id"] == chat_id)


def _make_older(chat_id, seq, by: timedelta) -> None:
    with SessionLocal() as db:
        db.execute(
            update(Message)
            .where(Message.chat_id == chat_id, Message.seq == seq)
            .values(created_at=datetime.now(UTC) - by)
        )
        db.commit()


def _raw(chat_id, seq) -> Message:
    with SessionLocal() as db:
        return db.scalar(select(Message).where(Message.chat_id == chat_id, Message.seq == seq))


@contextmanager
def _open_line(client, me):
    ticket = client.post("/api/live/ticket", headers=me).json()["ticket"]
    with client.websocket_connect(f"/api/live?ticket={ticket}") as line:
        assert line.receive_json()["type"] == "hello"
        yield line


@pytest.fixture
def pair(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    return ana, ben, _start_chat(client, ana, "ben@example.com")


@pytest.fixture
def trio(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    return ana, ben, cara, _group(client, ana, "Ben", "Cara")


# --- Reactions ---


def test_a_reaction_shows_who_and_takes_a_number(client, pair):
    ana, ben, chat_id = pair
    ben_id = _my_id(client, ben)
    _send(client, ana, chat_id)

    reply = _react(client, ben, chat_id, 1)

    assert reply.status_code == 200
    assert reply.json()["seq"] == 1  # the reply is the message, not the event
    assert reply.json()["reactions"] == {THUMBS: [ben_id]}
    assert reply.json()["state_seq"] == 2
    event = _raw(chat_id, 2)
    assert (event.kind, event.body, event.data) == ("reaction", "", {"target_seq": 1})


def test_one_reaction_per_person_a_new_one_replaces_it(client, pair):
    ana, ben, chat_id = pair
    ben_id, ana_id = _my_id(client, ben), _my_id(client, ana)
    _send(client, ana, chat_id)

    _react(client, ben, chat_id, 1, THUMBS)
    _react(client, ana, chat_id, 1, THUMBS)
    reply = _react(client, ben, chat_id, 1, HEART)

    assert reply.json()["reactions"] == {THUMBS: [ana_id], HEART: [ben_id]}
    with SessionLocal() as db:
        assert len(db.scalars(select(Reaction)).all()) == 2


def test_removing_a_reaction_and_doing_it_twice_takes_no_number(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id)

    _react(client, ben, chat_id, 1)
    assert _react(client, ben, chat_id, 1).json()["state_seq"] == 2  # the same one again: nothing new
    assert _unreact(client, ben, chat_id, 1).json()["reactions"] == {}
    assert _unreact(client, ben, chat_id, 1).json()["state_seq"] == 3  # already gone: nothing new
    assert _row(client, ana, chat_id)["last_message"]["seq"] == 1
    with SessionLocal() as db:
        assert db.execute(text("SELECT last_seq FROM chats")).scalar() == 3


def test_only_the_six_emojis_are_allowed(client, pair):
    ana, _, chat_id = pair
    _send(client, ana, chat_id)
    assert _react(client, ana, chat_id, 1, "🤡").status_code == 422
    for emoji in ("👍", "❤️", "😂", "😮", "😢", "🙏"):
        assert _react(client, ana, chat_id, 1, emoji).status_code == 200


def test_cant_react_to_a_group_note_or_an_event(client, trio):
    ana, ben, _, chat_id = trio
    assert _react(client, ben, chat_id, 1).status_code == 404  # #1 is the "created" note
    _send(client, ana, chat_id)
    _react(client, ben, chat_id, 2)
    assert _react(client, ben, chat_id, 3).status_code == 404  # #3 is a reaction event


def test_a_stranger_gets_404_for_every_action(client, pair, sign_up):
    ana, _, chat_id = pair
    stranger = sign_up("Eve")
    _send(client, ana, chat_id)
    assert _react(client, stranger, chat_id, 1).status_code == 404
    assert _unreact(client, stranger, chat_id, 1).status_code == 404
    assert _edit(client, stranger, chat_id, 1).status_code == 404
    assert _delete(client, stranger, chat_id, 1).status_code == 404


def test_someone_who_left_cant_act_any_more(client, trio):
    ana, ben, _, chat_id = trio
    mine = _send(client, ben, chat_id)["seq"]
    assert client.post(f"/api/chats/{chat_id}/leave", headers=ben).status_code == 200
    assert _react(client, ben, chat_id, mine).status_code == 403
    assert _edit(client, ben, chat_id, mine).status_code == 403
    assert _delete(client, ben, chat_id, mine).status_code == 403
    assert _react(client, ana, chat_id, mine).status_code == 200  # the others still can


def test_a_new_member_cant_touch_messages_from_before_they_joined(client, trio, sign_up):
    ana, _, _, chat_id = trio
    dev = sign_up("Dev")
    old = _send(client, ana, chat_id)["seq"]
    response = client.post(
        f"/api/chats/{chat_id}/members", json={"emails": ["dev@example.com"], "user_ids": []}, headers=ana
    )
    assert response.status_code == 200
    assert _react(client, dev, chat_id, old).status_code == 404


# --- Edit ---


def test_editing_my_text_changes_it_everywhere_and_marks_it_edited(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id, "helo")

    reply = _edit(client, ana, chat_id, 1, "  hello  ")

    assert reply.status_code == 200
    assert (reply.json()["body"], reply.json()["edited"]) == ("hello", True)
    message = _history(client, ben, chat_id)["messages"][0]
    assert (message["body"], message["edited"]) == ("hello", True)
    assert _row(client, ben, chat_id)["last_message"]["preview"] == "hello"
    # The event itself holds no text: the message is the only copy.
    event = _raw(chat_id, 2)
    assert (event.kind, event.body, event.data) == ("edit", "", {"target_seq": 1})


def test_only_my_own_text_can_be_edited(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id)
    reply = _edit(client, ben, chat_id, 1)
    assert reply.status_code == 403
    assert _raw(chat_id, 1).body == "hello"


def test_a_file_cant_be_edited(client, pair):
    ana, _, chat_id = pair
    with SessionLocal() as db:
        db.execute(text("UPDATE chats SET last_seq = 1"))
        sender = uuid.UUID(_my_id(client, ana))
        db.add(
            Message(
                chat_id=uuid.UUID(chat_id), seq=1, sender_id=sender, client_msg_id=uuid.uuid4(),
                body="", kind="file", data={"file_id": "x"},
            )
        )
        db.commit()
    assert _edit(client, ana, chat_id, 1).status_code == 400


def test_edit_allowed_up_to_15_minutes_then_refused(client, pair):
    ana, _, chat_id = pair
    _send(client, ana, chat_id)

    _make_older(chat_id, 1, timedelta(minutes=14, seconds=50))
    assert _edit(client, ana, chat_id, 1, "in time").status_code == 200

    _make_older(chat_id, 1, timedelta(minutes=15, seconds=10))
    reply = _edit(client, ana, chat_id, 1, "too late")
    assert reply.status_code == 403
    assert _raw(chat_id, 1).body == "in time"


def test_saving_the_same_text_takes_no_number_and_isnt_edited(client, pair):
    ana, _, chat_id = pair
    _send(client, ana, chat_id)
    reply = _edit(client, ana, chat_id, 1, "hello")
    assert (reply.json()["edited"], reply.json()["state_seq"]) == (False, 0)


def test_edit_text_is_checked_like_a_send(client, pair):
    ana, _, chat_id = pair
    _send(client, ana, chat_id)
    assert _edit(client, ana, chat_id, 1, "   ").status_code == 422
    assert _edit(client, ana, chat_id, 1, "x" * 4001).status_code == 422


# --- Delete for everyone ---


def test_deleting_erases_the_text_and_reactions_for_everyone(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id, "a secret")
    _react(client, ben, chat_id, 1)

    reply = _delete(client, ana, chat_id, 1)

    assert reply.status_code == 200
    assert (reply.json()["deleted"], reply.json()["body"], reply.json()["reactions"]) == (True, "", {})
    # Really gone from the database, the row and the event alike.
    assert _raw(chat_id, 1).body == ""
    with SessionLocal() as db:
        assert db.execute(text("SELECT count(*) FROM messages WHERE body LIKE '%secret%'")).scalar() == 0
        assert db.execute(text("SELECT count(*) FROM message_reactions")).scalar() == 0
    shown = _history(client, ben, chat_id)["messages"][0]
    assert (shown["deleted"], shown["body"], shown["data"]) == (True, "", None)
    last = _row(client, ben, chat_id)["last_message"]
    assert (last["deleted"], last["preview"], last["seq"]) == (True, "", 1)


def test_only_my_own_can_be_deleted(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id)
    assert _delete(client, ben, chat_id, 1).status_code == 403
    assert _raw(chat_id, 1).deleted_at is None


def test_even_an_admin_cant_delete_someone_elses(client, trio):
    ana, ben, _, chat_id = trio
    seq = _send(client, ben, chat_id)["seq"]
    assert _delete(client, ana, chat_id, seq).status_code == 403


def test_delete_allowed_up_to_1_hour_then_refused(client, pair):
    ana, _, chat_id = pair
    _send(client, ana, chat_id, "one")
    _send(client, ana, chat_id, "two")

    _make_older(chat_id, 1, timedelta(minutes=59, seconds=50))
    assert _delete(client, ana, chat_id, 1).status_code == 200

    _make_older(chat_id, 2, timedelta(hours=1, seconds=10))
    assert _delete(client, ana, chat_id, 2).status_code == 403
    assert _raw(chat_id, 2).body == "two"


def test_deleting_twice_takes_no_new_number(client, pair):
    ana, _, chat_id = pair
    _send(client, ana, chat_id)
    _delete(client, ana, chat_id, 1)
    again = _delete(client, ana, chat_id, 1)
    assert (again.status_code, again.json()["state_seq"]) == (200, 2)


def test_a_deleted_message_cant_be_reacted_to_or_edited(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id)
    _delete(client, ana, chat_id, 1)
    assert _react(client, ben, chat_id, 1).status_code == 400
    assert _edit(client, ana, chat_id, 1).status_code == 400


# --- Deleting a file ---


def _send_file(client, me, chat_id) -> tuple[str, int, str]:
    """A real upload through the real store. Returns (file id, message number, key)."""
    body = b"pretend this is a picture"
    grant = client.post(
        f"/api/chats/{chat_id}/uploads", json={"name": "holiday.png", "type": "image/png", "size": len(body)}, headers=me
    ).json()
    url = store.endpoint + grant["url"].removeprefix(store.public_url)
    request = urllib.request.Request(url, method="PUT", data=body, headers={"Content-Type": "image/png"})
    urllib.request.urlopen(request, timeout=10).close()
    sent = client.post(
        f"/api/chats/{chat_id}/files",
        json={"client_msg_id": str(uuid.uuid4()), "file_id": grant["file_id"]},
        headers=me,
    ).json()
    with SessionLocal() as db:
        key = db.get(Upload, uuid.UUID(grant["file_id"])).key
    return grant["file_id"], sent["seq"], key


def test_deleting_a_file_removes_it_from_the_store_and_the_lists(client, pair):
    ana, ben, chat_id = pair
    file_id, seq, key = _send_file(client, ana, chat_id)
    assert store.head(key) is not None

    reply = _delete(client, ana, chat_id, seq)

    assert (reply.status_code, reply.json()["data"]) == (200, None)
    assert store.head(key) is None
    with SessionLocal() as db:
        assert db.get(Upload, uuid.UUID(file_id)) is None
    assert client.get(f"/api/chats/{chat_id}/files/{file_id}/url", headers=ben).status_code == 404
    assert client.get(f"/api/chats/{chat_id}/files", headers=ben).json()["messages"] == []


def test_a_store_outage_leaves_the_erase_owed_and_cleanup_finishes_it(client, pair, monkeypatch):
    ana, _, chat_id = pair
    file_id, seq, key = _send_file(client, ana, chat_id)

    def store_down(_key):
        raise StoreError("down")

    monkeypatch.setattr(cleanup.store, "delete", store_down)
    reply = _delete(client, ana, chat_id, seq)
    monkeypatch.undo()

    # The message is deleted anyway, and no link can be made for the file...
    assert reply.status_code == 200
    with SessionLocal() as db:
        owed = db.get(Upload, uuid.UUID(file_id))
        assert (owed.erase_pending, owed.message_id, owed.name) == (True, None, "")
    assert client.get(f"/api/chats/{chat_id}/files/{file_id}/url", headers=ana).status_code == 404

    # ...and the next hourly run removes it, even though it's only minutes old.
    assert cleanup.remove_unsent() == 1
    assert store.head(key) is None
    with SessionLocal() as db:
        assert db.get(Upload, uuid.UUID(file_id)) is None


def test_cleanup_still_leaves_a_young_unsent_upload_alone(client, pair):
    ana, _, chat_id = pair
    grant = client.post(
        f"/api/chats/{chat_id}/uploads", json={"name": "a.png", "type": "image/png", "size": 5}, headers=ana
    ).json()
    assert cleanup.remove_unsent() == 0
    with SessionLocal() as db:
        assert db.get(Upload, uuid.UUID(grant["file_id"])) is not None


# --- History and catch-up ---


def test_history_has_the_latest_state_and_no_events(client, pair):
    ana, ben, chat_id = pair
    ben_id = _my_id(client, ben)
    _send(client, ana, chat_id, "one")  # 1
    _send(client, ana, chat_id, "two")  # 2
    _send(client, ana, chat_id, "three")  # 3
    _react(client, ben, chat_id, 1)  # 4
    _edit(client, ana, chat_id, 2, "TWO")  # 5
    _delete(client, ana, chat_id, 3)  # 6

    page = _history(client, ben, chat_id)

    by_seq = {message["seq"]: message for message in page["messages"]}
    assert sorted(by_seq) == [1, 2, 3]
    assert by_seq[1]["reactions"] == {THUMBS: [ben_id]}
    assert (by_seq[2]["body"], by_seq[2]["edited"]) == ("TWO", True)
    assert by_seq[3]["deleted"] is True
    # The numbers left out are settled too, so the app sees no holes.
    assert (page["low_seq"], page["high_seq"]) == (1, 6)


def test_an_older_page_settles_the_numbers_between_it_and_the_next(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id, "one")  # 1
    _send(client, ana, chat_id, "two")  # 2
    _react(client, ben, chat_id, 1)  # 3
    _send(client, ana, chat_id, "three")  # 4

    newest = _history(client, ben, chat_id, "?limit=1")
    assert ([m["seq"] for m in newest["messages"]], newest["has_more"]) == ([4], True)
    assert (newest["low_seq"], newest["high_seq"]) == (4, 4)

    older = _history(client, ben, chat_id, "?before=4")
    assert [m["seq"] for m in older["messages"]] == [2, 1]
    assert (older["low_seq"], older["high_seq"]) == (1, 3)


def test_an_empty_page_settles_nothing(client, pair):
    ana, _, chat_id = pair
    page = _history(client, ana, chat_id)
    assert (page["low_seq"], page["high_seq"]) == (None, None)
    _send(client, ana, chat_id)
    page = _history(client, ana, chat_id, "?after=1")
    assert (page["messages"], page["low_seq"], page["high_seq"]) == ([], None, None)


def test_catch_up_brings_the_changes_with_the_message_as_it_is_now(client, pair):
    ana, ben, chat_id = pair
    ben_id = _my_id(client, ben)
    _send(client, ana, chat_id, "one")  # 1
    _react(client, ben, chat_id, 1)  # 2
    _edit(client, ana, chat_id, 1, "ONE")  # 3

    page = _history(client, ben, chat_id, "?after=1")

    assert [(m["seq"], m["kind"]) for m in page["messages"]] == [(2, "reaction"), (3, "edit")]
    target = page["messages"][0]["target"]
    assert (target["seq"], target["body"], target["reactions"], target["state_seq"]) == (1, "ONE", {THUMBS: [ben_id]}, 3)
    assert (page["low_seq"], page["high_seq"]) == (2, 3)


def test_catch_up_hides_the_message_from_someone_who_joined_later(client, trio, sign_up):
    ana, ben, _, chat_id = trio
    dev = sign_up("Dev")
    old = _send(client, ana, chat_id, "before Dev")["seq"]
    client.post(f"/api/chats/{chat_id}/members", json={"emails": ["dev@example.com"], "user_ids": []}, headers=ana)
    joined = _history(client, dev, chat_id)["low_seq"]
    _react(client, ben, chat_id, old)

    page = _history(client, dev, chat_id, f"?after={joined}")

    assert [(m["kind"], m["target"]) for m in page["messages"]] == [("reaction", None)]


# --- Live pushes ---


def test_a_change_is_pushed_to_both_people_with_the_new_state(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id, "helo")

    with _open_line(client, ana) as anas_line, _open_line(client, ben) as bens_line:
        assert anas_line.receive_json()["type"] == "presence"  # Ben came online
        _edit(client, ana, chat_id, 1, "hello")

        for line in (anas_line, bens_line):
            event = line.receive_json()
            assert (event["type"], event["data"]["kind"], event["data"]["seq"]) == ("message.new", "edit", 2)
            assert event["data"]["target"]["body"] == "hello"
            assert event["data"]["data"] == {"target_seq": 1}


def test_the_push_hides_the_message_from_someone_who_joined_later(client, trio, sign_up):
    ana, ben, _, chat_id = trio
    dev = sign_up("Dev")
    old = _send(client, ana, chat_id, "before Dev")["seq"]
    client.post(f"/api/chats/{chat_id}/members", json={"emails": ["dev@example.com"], "user_ids": []}, headers=ana)

    with _open_line(client, dev) as devs_line, _open_line(client, ben) as bens_line:
        _react(client, ben, chat_id, old)
        seen_by_dev = devs_line.receive_json()["data"]
        seen_by_ben = bens_line.receive_json()["data"]

    assert seen_by_dev["kind"] == "reaction"
    assert seen_by_dev["target"] is None
    assert seen_by_ben["target"]["body"] == "before Dev"


def test_someone_who_left_gets_no_push(client, trio):
    ana, ben, _, chat_id = trio
    seq = _send(client, ana, chat_id)["seq"]
    client.post(f"/api/chats/{chat_id}/leave", headers=ben)

    with _open_line(client, ben) as bens_line, _open_line(client, ana) as anas_line:
        _react(client, ana, chat_id, seq)
        assert anas_line.receive_json()["data"]["kind"] == "reaction"
        _send(client, ana, chat_id, "only for those still here")
        anas_line.receive_json()
        # Ben's line stays silent. A ping proves it's alive, and the pong is the first thing back.
        bens_line.send_json({"type": "ping"})
        assert bens_line.receive_json()["type"] == "pong"


# --- Unread and notifications ---


def test_unread_counts_only_real_messages(client, trio):
    ana, ben, cara, chat_id = trio
    assert _row(client, ben, chat_id)["unread"] == 0  # #1, the "created" note, doesn't count

    _send(client, ana, chat_id, "one")  # 2
    _send(client, ana, chat_id, "two")  # 3
    _react(client, cara, chat_id, 2)  # 4
    _edit(client, ana, chat_id, 3, "TWO")  # 5
    assert client.patch(f"/api/chats/{chat_id}", json={"name": "Renamed"}, headers=ana).status_code == 200  # 6, a note

    assert _row(client, ben, chat_id)["unread"] == 2


def test_my_own_reaction_doesnt_mark_newer_messages_as_read(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id, "one")
    _send(client, ana, chat_id, "two")
    _react(client, ben, chat_id, 1)
    assert _row(client, ben, chat_id)["unread"] == 2


def test_reading_past_the_events_clears_unread(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id)
    _react(client, ana, chat_id, 1)
    assert client.post(f"/api/chats/{chat_id}/read", json={"seq": 2}, headers=ben).status_code == 200
    assert _row(client, ben, chat_id)["unread"] == 0


def test_the_chat_list_preview_skips_events(client, pair):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id, "one")
    _react(client, ben, chat_id, 1)

    last = _row(client, ben, chat_id)["last_message"]

    assert (last["seq"], last["kind"], last["preview"]) == (1, "text", "one")


def test_the_preview_of_someone_who_left_stops_at_their_note(client, trio):
    ana, ben, _, chat_id = trio
    seq = _send(client, ana, chat_id, "before")["seq"]
    client.post(f"/api/chats/{chat_id}/leave", headers=ben)
    _react(client, ana, chat_id, seq)
    _send(client, ana, chat_id, "after")

    last = _row(client, ben, chat_id)["last_message"]

    assert (last["kind"], last["data"]["event"]) == ("system", "left")


def test_events_make_no_notification_jobs(client, pair, rabbit):
    ana, ben, chat_id = pair
    _send(client, ana, chat_id)
    jobs_after_the_send = rabbit.queue_declare("notify.wait", passive=True).method.message_count
    assert jobs_after_the_send == 1

    _react(client, ben, chat_id, 1)
    _edit(client, ana, chat_id, 1, "x")

    assert rabbit.queue_declare("notify.wait", passive=True).method.message_count == 1


def test_a_notification_for_a_deleted_message_is_skipped(client, pair):
    ana, ben, chat_id = pair
    sent = _send(client, ana, chat_id)
    ben_id = uuid.UUID(_my_id(client, ben))
    _delete(client, ana, chat_id, 1)

    outcome = worker.handle(Job(uuid.UUID(sent["id"]), uuid.UUID(chat_id), 1, ben_id), attempt=1)

    assert outcome == "skip: message or member gone"


# --- Limits ---


def test_changes_share_the_send_limit(client, pair):
    ana, _, chat_id = pair
    _send(client, ana, chat_id)
    statuses = [_react(client, ana, chat_id, 1, THUMBS if i % 2 else LAUGH).status_code for i in range(25)]
    assert statuses.count(429) > 0
