"""Status (D41): 24-hour texts and photos, seen by the people I have a direct
chat with. Photos go to the real store, like chat files (test_files.py)."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.db import SessionLocal
from app.live import bus
from app.status import cleanup
from app.status.models import Status, StatusView
from app.status.service import now, status_key
from tests.test_files import BODY, PNG, _call, _my_id, _start_chat
from app.files.store import store


def _text(client, me, body="Off to the beach", **extra):
    return client.post("/api/status", json={"id": str(uuid.uuid4()), "kind": "text", "body": body, **extra}, headers=me)


def _feed(client, me):
    reply = client.get("/api/status", headers=me)
    assert reply.status_code == 200
    return reply.json()


def _new_upload(client, me, status_id, content_type=PNG, size=len(BODY)):
    return client.post("/api/status/uploads", json={"id": status_id, "type": content_type, "size": size}, headers=me)


def _photo(client, me, body=BODY, caption="") -> dict:
    """Uploads for real and posts. Returns the status."""
    status_id = str(uuid.uuid4())
    reply = _new_upload(client, me, status_id, size=len(body))
    assert reply.status_code == 201
    assert _call("PUT", reply.json()["url"], body, PNG)[0] == 200
    posted = client.post(
        "/api/status", json={"id": status_id, "kind": "image", "body": caption, "width": 4, "height": 3}, headers=me
    )
    assert posted.status_code == 201
    return posted.json()


def _run_out(status_id: str) -> None:
    """As if its 24 hours were up."""
    with SessionLocal() as db:
        db.execute(update(Status).where(Status.id == uuid.UUID(status_id)).values(expires_at=now() - timedelta(seconds=1)))
        db.commit()


@pytest.fixture
def people(client, sign_up):
    """Ana and Ben share a direct chat. Cara knows nobody."""
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    chat_id = _start_chat(client, ana, "ben@example.com")
    return ana, ben, cara, chat_id


@pytest.fixture
def pushes(monkeypatch):
    """Every live push, as (who, event), instead of going to Redis."""
    sent = []
    monkeypatch.setattr(bus, "publish", lambda users, event: sent.append((set(users), event)))
    return sent


# --- Who sees what ---


def test_a_text_status_reaches_the_people_i_chat_with(client, people):
    ana, ben, cara, _ = people
    posted = _text(client, ana, "Off to the beach", color=3)
    assert posted.status_code == 201
    assert posted.json()["body"] == "Off to the beach"
    assert posted.json()["color"] == 3

    feed = _feed(client, ben)
    assert feed["mine"] == []
    [person] = feed["people"]
    assert person["name"] == "Ana"
    assert person["all_viewed"] is False
    assert [s["body"] for s in person["statuses"]] == ["Off to the beach"]
    # Someone else's view count is not mine to know
    assert person["statuses"][0]["views"] is None

    # Cara has no chat with Ana, so she sees nothing
    assert _feed(client, cara)["people"] == []
    # And Ana sees her own, with its count
    [mine] = _feed(client, ana)["mine"]
    assert (mine["views"], mine["viewed"]) == (0, True)


def test_it_lasts_24_hours(client, people):
    ana, _, _, _ = people
    posted = _text(client, ana).json()
    from datetime import datetime

    lasts = datetime.fromisoformat(posted["expires_at"]) - datetime.fromisoformat(posted["posted_at"])
    assert lasts == timedelta(hours=24)


def test_a_group_alone_doesnt_share_statuses(client, people):
    ana, _, cara, _ = people
    group = client.post("/api/chats/groups", json={"name": "Trip", "emails": ["cara@example.com"], "user_ids": []}, headers=ana)
    assert group.status_code == 201
    _text(client, ana)
    assert _feed(client, cara)["people"] == []


def test_people_are_listed_newest_first_and_statuses_oldest_first(client, people, sign_up):
    ana, ben, _, _ = people
    dan = sign_up("Dan")
    _start_chat(client, ben, "dan@example.com")
    _text(client, ana, "one")
    _text(client, ana, "two")
    _text(client, dan, "three")
    feed = _feed(client, ben)
    assert [p["name"] for p in feed["people"]] == ["Dan", "Ana"]
    assert [s["body"] for s in feed["people"][1]["statuses"]] == ["one", "two"]


# --- Posting ---


def test_a_retried_post_is_saved_once_and_told_once(client, people, pushes):
    ana, _, _, _ = people
    body = {"id": str(uuid.uuid4()), "kind": "text", "body": "hi"}
    first = client.post("/api/status", json=body, headers=ana)
    second = client.post("/api/status", json=body, headers=ana)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]
    assert len(_feed(client, ana)["mine"]) == 1
    assert len(pushes) == 1


def test_a_post_tells_my_people_and_my_tabs(client, people, pushes):
    ana, ben, _, _ = people
    _text(client, ana)
    [(who, event)] = pushes
    assert who == {uuid.UUID(_my_id(client, ana)), uuid.UUID(_my_id(client, ben))}
    assert event == {"type": "status", "data": {"user_id": _my_id(client, ana), "change": "new"}}


def test_someone_elses_id_is_refused(client, people):
    ana, ben, _, _ = people
    body = {"id": str(uuid.uuid4()), "kind": "text", "body": "mine"}
    assert client.post("/api/status", json=body, headers=ana).status_code == 201
    assert client.post("/api/status", json=body | {"body": "taken"}, headers=ben).status_code == 409


@pytest.mark.parametrize("extra", [{"body": "   "}, {"body": "x" * 701}, {"color": 6}, {"kind": "video"}])
def test_a_bad_text_status_is_refused(client, people, extra):
    ana, _, _, _ = people
    body = {"id": str(uuid.uuid4()), "kind": "text", "body": "hi"} | extra
    assert client.post("/api/status", json=body, headers=ana).status_code == 422


def test_posting_needs_a_login(client):
    assert client.post("/api/status", json={"id": str(uuid.uuid4()), "kind": "text", "body": "hi"}).status_code == 401
    assert client.get("/api/status").status_code == 401


def test_posts_are_limited_per_user(client, people):
    ana, _, _, _ = people
    replies = [_text(client, ana).status_code for _ in range(31)]
    assert replies[:30] == [201] * 30
    assert replies[30] == 429


# --- Views ---


def test_a_view_is_counted_once_and_only_the_poster_sees_who(client, people, pushes):
    ana, ben, _, _ = people
    status_id = _text(client, ana).json()["id"]
    pushes.clear()
    assert client.post(f"/api/status/{status_id}/view", headers=ben).status_code == 204
    assert client.post(f"/api/status/{status_id}/view", headers=ben).status_code == 204
    # Only the first view tells Ana
    assert [event["data"]["change"] for _, event in pushes] == ["viewed"]

    [mine] = _feed(client, ana)["mine"]
    assert mine["views"] == 1
    viewers = client.get(f"/api/status/{status_id}/views", headers=ana).json()
    assert [v["name"] for v in viewers] == ["Ben"]
    # Ben may not ask who else saw it
    assert client.get(f"/api/status/{status_id}/views", headers=ben).status_code == 404
    # And Ben's ring turns grey
    assert _feed(client, ben)["people"][0]["all_viewed"] is True


def test_my_own_views_dont_count(client, people):
    ana, _, _, _ = people
    status_id = _text(client, ana).json()["id"]
    assert client.post(f"/api/status/{status_id}/view", headers=ana).status_code == 204
    assert _feed(client, ana)["mine"][0]["views"] == 0


def test_a_stranger_cant_view_or_list(client, people):
    ana, _, cara, _ = people
    status_id = _text(client, ana).json()["id"]
    assert client.post(f"/api/status/{status_id}/view", headers=cara).status_code == 404
    assert client.get(f"/api/status/{status_id}/views", headers=cara).status_code == 404
    with SessionLocal() as db:
        assert db.scalars(select(StatusView)).all() == []


# --- Running out ---


def test_a_run_out_status_is_gone_everywhere(client, people):
    ana, ben, _, _ = people
    status_id = _text(client, ana).json()["id"]
    _run_out(status_id)
    assert _feed(client, ben)["people"] == []
    assert _feed(client, ana)["mine"] == []
    assert client.post(f"/api/status/{status_id}/view", headers=ben).status_code == 404
    assert client.get(f"/api/status/{status_id}/views", headers=ana).status_code == 404


def test_the_hourly_job_removes_run_out_statuses_and_their_photos(client, people):
    ana, _, _, _ = people
    keep = _text(client, ana).json()["id"]
    text_id = _text(client, ana).json()["id"]
    photo = _photo(client, ana)
    _run_out(text_id)
    _run_out(photo["id"])

    assert cleanup.remove_expired() == 2
    with SessionLocal() as db:
        assert [str(s.id) for s in db.scalars(select(Status))] == [keep]
    assert store.head(status_key(uuid.UUID(_my_id(client, ana)), uuid.UUID(photo["id"]))) is None


def test_a_photo_never_posted_is_removed_after_a_day(client, people):
    ana, _, _, _ = people
    status_id = str(uuid.uuid4())
    assert _new_upload(client, ana, status_id).status_code == 201
    assert cleanup.remove_expired() == 0  # not yet
    with SessionLocal() as db:
        db.execute(update(Status).values(created_at=now() - timedelta(days=1, minutes=1)))
        db.commit()
    assert cleanup.remove_expired() == 1


# --- Photos ---


def test_a_photo_status_reaches_my_people_only(client, people):
    ana, ben, cara, _ = people
    posted = _photo(client, ana, caption="Sunset")
    assert (posted["kind"], posted["body"], posted["width"], posted["height"]) == ("image", "Sunset", 4, 3)

    link = client.get(f"/api/status/{posted['id']}/url", headers=ben)
    assert link.status_code == 200
    status, body, _ = _call("GET", link.json()["url"])
    assert (status, body) == (200, BODY)
    assert client.get(f"/api/status/{posted['id']}/url", headers=cara).status_code == 404


def test_a_photo_waits_for_its_upload(client, people):
    ana, ben, _, _ = people
    status_id = str(uuid.uuid4())
    assert _new_upload(client, ana, status_id).status_code == 201
    post = {"id": status_id, "kind": "image"}
    assert client.post("/api/status", json=post, headers=ana).status_code == 409
    # Not posted, so nobody sees it, not even me
    assert _feed(client, ben)["people"] == []
    assert _feed(client, ana)["mine"] == []
    assert client.get(f"/api/status/{status_id}/url", headers=ana).status_code == 404


def test_a_photo_needs_an_upload_first(client, people):
    ana, _, _, _ = people
    assert client.post("/api/status", json={"id": str(uuid.uuid4()), "kind": "image"}, headers=ana).status_code == 409


def test_a_photo_that_doesnt_match_its_upload_is_refused(client, people):
    ana, _, _, _ = people
    status_id = str(uuid.uuid4())
    reply = _new_upload(client, ana, status_id)
    assert _call("PUT", reply.json()["url"], BODY, PNG)[0] == 200
    # As if the upload had claimed a different size
    with SessionLocal() as db:
        row = db.get(Status, uuid.UUID(status_id))
        row.data = row.data | {"size": len(BODY) + 1}
        db.commit()
    assert client.post("/api/status", json={"id": status_id, "kind": "image"}, headers=ana).status_code == 422


@pytest.mark.parametrize("content_type", ["application/pdf", "audio/webm", "image/svg+xml"])
def test_only_photos_can_be_uploaded(client, people, content_type):
    ana, _, _, _ = people
    assert _new_upload(client, ana, str(uuid.uuid4()), content_type=content_type).status_code == 422


def test_a_text_id_cant_become_a_photo(client, people):
    ana, _, _, _ = people
    status_id = _text(client, ana).json()["id"]
    assert _new_upload(client, ana, status_id).status_code == 409


# --- Deleting ---


def test_deleting_takes_it_down_for_everyone(client, people, pushes):
    ana, ben, _, _ = people
    photo = _photo(client, ana)
    pushes.clear()
    assert client.delete(f"/api/status/{photo['id']}", headers=ana).status_code == 204
    assert _feed(client, ben)["people"] == []
    assert [event["data"]["change"] for _, event in pushes] == ["gone"]
    with SessionLocal() as db:
        assert db.get(Status, uuid.UUID(photo["id"])) is None
    assert store.head(status_key(uuid.UUID(_my_id(client, ana)), uuid.UUID(photo["id"]))) is None


def test_only_the_poster_can_delete(client, people):
    ana, ben, _, _ = people
    status_id = _text(client, ana).json()["id"]
    assert client.delete(f"/api/status/{status_id}", headers=ben).status_code == 404
    assert len(_feed(client, ben)["people"]) == 1


# --- Replies ---


def _reply(client, me, chat_id, status_id, body="Nice!"):
    return client.post(
        f"/api/chats/{chat_id}/messages",
        json={"client_msg_id": str(uuid.uuid4()), "body": body, "status_id": status_id},
        headers=me,
    )


def test_a_reply_goes_into_our_chat_with_a_copy_of_the_status(client, people):
    ana, ben, _, chat_id = people
    status_id = _text(client, ana, "Off to the beach", color=2).json()["id"]
    reply = _reply(client, ben, chat_id, status_id)
    assert reply.status_code == 201
    assert reply.json()["body"] == "Nice!"
    assert reply.json()["data"] == {
        "status": {"id": status_id, "kind": "text", "body": "Off to the beach", "color": 2, "preview": None}
    }
    # Still there after the status is gone
    _run_out(status_id)
    cleanup.remove_expired()
    [message] = client.get(f"/api/chats/{chat_id}/messages", headers=ana).json()["messages"]
    assert message["data"]["status"]["body"] == "Off to the beach"


def test_a_reply_to_a_status_that_cant_be_quoted_is_a_plain_message(client, people, sign_up):
    ana, ben, cara, chat_id = people
    status_id = _text(client, ana).json()["id"]
    # In a chat with someone else: no copy
    other = _start_chat(client, ben, "cara@example.com")
    assert _reply(client, ben, other, status_id).json()["data"] is None
    # My own status: no copy
    assert _reply(client, ana, chat_id, status_id).json()["data"] is None
    # Run out: no copy, and still sent
    _run_out(status_id)
    reply = _reply(client, ben, chat_id, status_id)
    assert (reply.status_code, reply.json()["data"]) == (201, None)
