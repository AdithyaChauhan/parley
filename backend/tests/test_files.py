"""Files and voice notes (D38), against the real store. Nginx's part is checked
in the browser run, so the URLs here go straight to the store."""

import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.db import SessionLocal
from app.files import cleanup, routes, s3
from app.files.models import Upload
from app.files.s3 import ObjectInfo, Store, StoreError
from app.files.store import MAX_FILE_BYTES, store

PNG = "image/png"
PDF = "application/pdf"
BODY = b"pretend this is a picture"


def _start_chat(client, me, email) -> str:
    response = client.post("/api/chats/direct", json={"email": email}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _group(client, me, *names) -> str:
    emails = [f"{n.lower()}@example.com" for n in names]
    response = client.post("/api/chats/groups", json={"name": "Trip", "emails": emails, "user_ids": []}, headers=me)
    assert response.status_code == 201
    return response.json()["id"]


def _my_id(client, me) -> str:
    return client.get("/api/auth/me", headers=me).json()["id"]


def _new_upload(client, me, chat_id, name="a.png", content_type=PNG, size=len(BODY)):
    return client.post(
        f"/api/chats/{chat_id}/uploads", json={"name": name, "type": content_type, "size": size}, headers=me
    )


def _direct(url: str) -> str:
    """The browser's /storage/... URL, as the store itself sees it."""
    return store.endpoint + url.removeprefix(store.public_url)


def _call(method: str, url: str, data: bytes | None = None, content_type: str | None = None):
    request = urllib.request.Request(_direct(url), method=method, data=data)
    if content_type:
        request.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            return reply.status, reply.read(), reply.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.headers


def _upload(client, me, chat_id, body=BODY, name="a.png", content_type=PNG) -> str:
    """Asks for permission and uploads for real. Returns the file's id."""
    reply = _new_upload(client, me, chat_id, name, content_type, len(body))
    assert reply.status_code == 201
    status, _, _ = _call("PUT", reply.json()["url"], body, content_type)
    assert status == 200
    return reply.json()["file_id"]


def _send_file(client, me, chat_id, file_id, **extra):
    return client.post(
        f"/api/chats/{chat_id}/files",
        json={"client_msg_id": str(uuid.uuid4()), "file_id": file_id, **extra},
        headers=me,
    )


def _sent(client, me, chat_id, **kwargs) -> tuple[str, dict]:
    file_id = _upload(client, me, chat_id, **kwargs)
    reply = _send_file(client, me, chat_id, file_id)
    assert reply.status_code == 201
    return file_id, reply.json()


def _url(client, me, chat_id, file_id, query=""):
    return client.get(f"/api/chats/{chat_id}/files/{file_id}/url{query}", headers=me)


@pytest.fixture
def pair(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    return ana, ben, _start_chat(client, ana, "ben@example.com")


# --- Signing ---


def test_signature_matches_awss_published_example(monkeypatch):
    # AWS's own worked example for a presigned GET, so this is real Signature V4.
    class Fixed(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2013, 5, 24, tzinfo=UTC)

    monkeypatch.setattr(s3, "datetime", Fixed)
    aws = Store(
        "https://examplebucket.s3.amazonaws.com", "", "examplebucket", "us-east-1",
        "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    )
    monkeypatch.setattr(aws, "_path", lambda key: f"/{key}")  # their example has the bucket in the host
    query = aws._signed_query("GET", "test.txt", 86400, {}, {})
    assert query.endswith("X-Amz-Signature=aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404")


# --- The whole trip ---


def test_a_file_travels_from_one_member_to_the_other(client, pair):
    ana, ben, chat_id = pair
    file_id = _upload(client, ana, chat_id)

    reply = _send_file(client, ana, chat_id, file_id, width=800, height=600, preview="data:image/jpeg;base64,AAAA")
    assert reply.status_code == 201
    message = reply.json()
    assert message["kind"] == "file"
    assert message["body"] == ""
    assert message["data"]["name"] == "a.png"
    assert message["data"]["category"] == "image"
    assert message["data"]["size"] == len(BODY)
    assert message["data"]["width"] == 800

    url = _url(client, ben, chat_id, file_id)
    assert url.status_code == 200
    status, body, headers = _call("GET", url.json()["url"])
    assert status == 200
    assert body == BODY
    assert headers["Content-Type"] == PNG


def test_a_file_in_a_group_reaches_every_member(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    chat_id = _group(client, ana, "Ben", "Cara")
    file_id, _ = _sent(client, ana, chat_id)
    for member in (ana, ben, cara):
        assert _url(client, member, chat_id, file_id).status_code == 200


def test_a_voice_note_keeps_its_length(client, pair):
    ana, _, chat_id = pair
    file_id = _upload(client, ana, chat_id, name="voice.m4a", content_type="audio/mp4")
    reply = _send_file(client, ana, chat_id, file_id, duration_ms=4200)
    assert reply.json()["data"]["category"] == "voice"
    assert reply.json()["data"]["duration_ms"] == 4200


def test_a_voice_note_over_two_minutes_is_refused(client, pair):
    ana, _, chat_id = pair
    file_id = _upload(client, ana, chat_id, name="voice.m4a", content_type="audio/mp4")
    assert _send_file(client, ana, chat_id, file_id, duration_ms=120_001).status_code == 422


def test_documents_are_always_saved_not_opened(client, pair):
    ana, ben, chat_id = pair
    file_id, _ = _sent(client, ana, chat_id, name="plan final.pdf", content_type=PDF)
    _, _, headers = _call("GET", _url(client, ben, chat_id, file_id).json()["url"])
    assert headers["Content-Disposition"] == "attachment; filename*=UTF-8''plan%20final.pdf"


def test_an_image_opens_in_place_unless_downloaded(client, pair):
    ana, ben, chat_id = pair
    file_id, _ = _sent(client, ana, chat_id)
    _, _, inline = _call("GET", _url(client, ben, chat_id, file_id).json()["url"])
    assert inline["Content-Disposition"] is None
    _, _, saved = _call("GET", _url(client, ben, chat_id, file_id, "?download=true").json()["url"])
    assert "attachment" in saved["Content-Disposition"]


# --- Who may have a link ---


def test_a_non_member_cant_get_a_file_url(client, pair, sign_up):
    ana, _, chat_id = pair
    file_id, _ = _sent(client, ana, chat_id)
    stranger = sign_up("Eve")
    assert _url(client, stranger, chat_id, file_id).status_code == 404
    assert client.get(f"/api/chats/{chat_id}/files", headers=stranger).status_code == 404


def test_a_non_member_cant_upload(client, pair, sign_up):
    _, _, chat_id = pair
    assert _new_upload(client, sign_up("Eve"), chat_id).status_code == 404


def test_a_file_url_needs_a_login(client, pair):
    ana, _, chat_id = pair
    file_id, _ = _sent(client, ana, chat_id)
    assert client.get(f"/api/chats/{chat_id}/files/{file_id}/url").status_code == 401


def test_someone_who_left_gets_no_new_links_or_uploads(client, sign_up):
    ana, ben = sign_up("Ana"), sign_up("Ben")
    chat_id = _group(client, ana, "Ben")
    file_id, _ = _sent(client, ana, chat_id)
    assert client.post(f"/api/chats/{chat_id}/leave", headers=ben).status_code == 200

    assert _url(client, ben, chat_id, file_id).status_code == 403
    assert _new_upload(client, ben, chat_id).status_code == 403
    # What they already had still shows in their list (D37).
    assert len(client.get(f"/api/chats/{chat_id}/files", headers=ben).json()["messages"]) == 1


def test_a_new_member_cant_get_files_from_before_they_joined(client, sign_up):
    ana, ben, cara = sign_up("Ana"), sign_up("Ben"), sign_up("Cara")
    chat_id = _group(client, ana, "Ben")
    before, _ = _sent(client, ana, chat_id)
    added = client.post(f"/api/chats/{chat_id}/members", json={"emails": ["cara@example.com"], "user_ids": []}, headers=ana)
    assert added.status_code == 200
    after, _ = _sent(client, ana, chat_id)

    assert _url(client, cara, chat_id, before).status_code == 404
    assert _url(client, cara, chat_id, after).status_code == 200
    listed = client.get(f"/api/chats/{chat_id}/files", headers=cara).json()["messages"]
    assert [m["data"]["file_id"] for m in listed] == [after]


def test_a_url_for_another_chats_file_is_refused(client, pair, sign_up):
    ana, _, chat_id = pair
    file_id, _ = _sent(client, ana, chat_id)
    cara = sign_up("Cara")
    other_chat = _start_chat(client, cara, "ana@example.com")
    assert _url(client, cara, other_chat, file_id).status_code == 404


def test_an_unsent_file_has_no_link(client, pair):
    ana, _, chat_id = pair
    assert _url(client, ana, chat_id, _upload(client, ana, chat_id)).status_code == 404


# --- Size and type limits ---


def test_over_10_mb_is_refused(client, pair):
    ana, _, chat_id = pair
    assert _new_upload(client, ana, chat_id, size=MAX_FILE_BYTES + 1).status_code == 422
    assert _new_upload(client, ana, chat_id, size=MAX_FILE_BYTES).status_code == 201


@pytest.mark.parametrize("bad", ["text/html", "image/svg+xml", "application/x-msdownload", ""])
def test_a_type_not_on_the_list_is_refused(client, pair, bad):
    ana, _, chat_id = pair
    assert _new_upload(client, ana, chat_id, content_type=bad).status_code == 422


def test_the_store_refuses_more_bytes_than_were_signed(client, pair):
    ana, _, chat_id = pair
    url = _new_upload(client, ana, chat_id, size=len(BODY)).json()["url"]
    status, _, _ = _call("PUT", url, BODY + b"and then some", PNG)
    assert status == 403


def test_the_store_refuses_a_different_type_than_was_signed(client, pair):
    ana, _, chat_id = pair
    url = _new_upload(client, ana, chat_id).json()["url"]
    status, _, _ = _call("PUT", url, BODY, "text/html")
    assert status == 403


def test_a_stored_file_that_doesnt_match_is_refused(client, pair, monkeypatch):
    ana, _, chat_id = pair
    file_id = _upload(client, ana, chat_id)
    monkeypatch.setattr(routes.store, "head", lambda key: ObjectInfo(MAX_FILE_BYTES + 1, PNG))
    assert _send_file(client, ana, chat_id, file_id).status_code == 422


@pytest.mark.parametrize("name", ["../../etc/passwd", "C:\\temp\\evil.png"])
def test_a_file_name_is_only_ever_a_name(client, pair, name):
    ana, _, chat_id = pair
    file_id, message = _sent(client, ana, chat_id, name=name)
    assert "/" not in message["data"]["name"] and "\\" not in message["data"]["name"]
    with SessionLocal() as db:
        assert db.get(Upload, uuid.UUID(file_id)).key == f"chats/{chat_id}/{file_id}"


def test_a_preview_must_be_a_small_jpeg(client, pair):
    ana, _, chat_id = pair
    file_id = _upload(client, ana, chat_id)
    bad = "data:text/html;base64,PHNjcmlwdD4="
    assert _send_file(client, ana, chat_id, file_id, preview=bad).status_code == 422


def test_uploads_are_limited_per_user(client, pair):
    ana, _, chat_id = pair
    replies = [_new_upload(client, ana, chat_id).status_code for _ in range(61)]
    assert replies[:60] == [201] * 60
    assert replies[60] == 429


# --- Saved only after the upload finishes (D9) ---


def test_a_message_waits_for_the_upload_to_finish(client, pair):
    ana, ben, chat_id = pair
    file_id = _new_upload(client, ana, chat_id).json()["file_id"]
    assert _send_file(client, ana, chat_id, file_id).status_code == 409
    assert client.get(f"/api/chats/{chat_id}/messages", headers=ben).json()["messages"] == []


def test_a_retried_send_is_saved_once(client, pair):
    ana, _, chat_id = pair
    file_id = _upload(client, ana, chat_id)
    body = {"client_msg_id": str(uuid.uuid4()), "file_id": file_id}
    first = client.post(f"/api/chats/{chat_id}/files", json=body, headers=ana)
    second = client.post(f"/api/chats/{chat_id}/files", json=body, headers=ana)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]


def test_one_upload_cant_become_two_messages(client, pair):
    ana, _, chat_id = pair
    file_id = _upload(client, ana, chat_id)
    assert _send_file(client, ana, chat_id, file_id).status_code == 201
    assert _send_file(client, ana, chat_id, file_id).status_code == 409


def test_i_cant_send_someone_elses_upload(client, pair):
    ana, ben, chat_id = pair
    assert _send_file(client, ben, chat_id, _upload(client, ana, chat_id)).status_code == 404


def test_a_store_outage_says_try_again(client, pair, monkeypatch):
    ana, _, chat_id = pair
    file_id = _upload(client, ana, chat_id)

    def down(key):
        raise StoreError("no answer")

    monkeypatch.setattr(routes.store, "head", down)
    reply = _send_file(client, ana, chat_id, file_id)
    assert reply.status_code == 503
    assert "Retry-After" in reply.headers


# --- The chat's file list and the chat list ---


def test_the_file_list_is_newest_first_and_pages(client, pair):
    ana, ben, chat_id = pair
    ids = [_sent(client, ana, chat_id)[0] for _ in range(3)]
    client.post(
        f"/api/chats/{chat_id}/messages", json={"client_msg_id": str(uuid.uuid4()), "body": "not a file"}, headers=ana
    )
    page = client.get(f"/api/chats/{chat_id}/files?limit=2", headers=ben).json()
    assert [m["data"]["file_id"] for m in page["messages"]] == [ids[2], ids[1]]
    assert page["has_more"] is True
    oldest = page["messages"][-1]["seq"]
    rest = client.get(f"/api/chats/{chat_id}/files?before={oldest}", headers=ben).json()
    assert [m["data"]["file_id"] for m in rest["messages"]] == [ids[0]]
    assert rest["has_more"] is False


def test_the_chat_list_gets_the_files_details_without_its_picture(client, pair):
    ana, ben, chat_id = pair
    file_id = _upload(client, ana, chat_id)
    _send_file(client, ana, chat_id, file_id, preview="data:image/jpeg;base64,AAAA")
    last = client.get("/api/chats", headers=ben).json()[0]["last_message"]
    assert last["kind"] == "file"
    assert last["data"]["name"] == "a.png"
    assert "preview" not in last["data"]


def test_a_file_counts_as_unread_and_notifies_like_a_text(client, pair):
    ana, ben, chat_id = pair
    _sent(client, ana, chat_id)
    assert client.get("/api/chats", headers=ben).json()[0]["unread"] == 1


# --- Never sent: removed after a day ---


def _age(file_id: str, days: int) -> None:
    with SessionLocal() as db:
        db.execute(
            update(Upload)
            .where(Upload.id == uuid.UUID(file_id))
            .values(created_at=datetime.now(UTC) - timedelta(days=days))
        )
        db.commit()


def _exists(file_id: str, chat_id: str) -> bool:
    return store.head(f"chats/{chat_id}/{file_id}") is not None


def test_a_day_old_unsent_file_is_removed(client, pair):
    ana, _, chat_id = pair
    file_id = _upload(client, ana, chat_id)
    _age(file_id, 2)
    assert cleanup.remove_unsent() == 1
    assert not _exists(file_id, chat_id)
    with SessionLocal() as db:
        assert db.get(Upload, uuid.UUID(file_id)) is None


def test_a_recent_unsent_file_stays(client, pair):
    ana, _, chat_id = pair
    file_id = _upload(client, ana, chat_id)
    assert cleanup.remove_unsent() == 0
    assert _exists(file_id, chat_id)


def test_a_sent_file_is_never_removed(client, pair):
    ana, _, chat_id = pair
    file_id, _ = _sent(client, ana, chat_id)
    _age(file_id, 30)
    assert cleanup.remove_unsent() == 0
    assert _exists(file_id, chat_id)


def test_if_the_store_is_down_the_cleanup_tries_again_later(client, pair, monkeypatch):
    ana, _, chat_id = pair
    file_id = _upload(client, ana, chat_id)
    _age(file_id, 2)

    def down(key):
        raise StoreError("no answer")

    monkeypatch.setattr(cleanup.store, "delete", down)
    assert cleanup.remove_unsent() == 0
    with SessionLocal() as db:
        assert db.get(Upload, uuid.UUID(file_id)) is not None
