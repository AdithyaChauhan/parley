import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select

from app import busy
from app.auth.deps import get_current_user
from app.auth.models import User
from app.chats.models import ChatMember
from app.chats.service import get_member
from app.db import SessionLocal
from app.files.models import Upload
from app.files.s3 import StoreError
from app.files.schemas import FilePage, FileUrlOut, NewUploadOut, NewUploadRequest, SendFileRequest
from app.files.store import (
    ALLOWED_TYPES,
    DOWNLOAD_URL_SECONDS,
    MAX_FILE_BYTES,
    UPLOAD_URL_SECONDS,
    configured,
    file_key,
    store,
)
from app.limits import service as limits
from app.messages.models import Message
from app.messages.routes import save_and_push
from app.messages.schemas import MessageOut

router = APIRouter(prefix="/chats/{chat_id}", tags=["files"])


def _store_ready() -> None:
    if not configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "File storage isn't set up")


def _store_failed() -> HTTPException:
    # Treated like "busy" by the app: it tries again by itself (D34).
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, busy.DETAIL, headers=busy.retry_after())


def _member_or_404(db, chat_id: uuid.UUID, me: User) -> ChatMember:
    # The same 404 for "no such chat" and "not your chat" (messages/routes.py).
    member = get_member(db, chat_id, me.id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return member


@router.post("/uploads", response_model=NewUploadOut, status_code=status.HTTP_201_CREATED)
def new_upload(chat_id: uuid.UUID, body: NewUploadRequest, me: User = Depends(get_current_user)):
    """Permission to put one file in the store (D38). The browser then uploads it
    straight to the store. No message exists until that's done (D9)."""
    _store_ready()
    limits.enforce(limits.UPLOAD, me.id)
    if body.type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "This type of file isn't allowed")

    with SessionLocal() as db:
        if not _member_or_404(db, chat_id, me).current:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You're no longer a member of this group")
        upload_id = uuid.uuid4()
        key = file_key(chat_id, upload_id)
        db.add(
            Upload(
                id=upload_id, chat_id=chat_id, user_id=me.id, key=key,
                name=body.name, content_type=body.type, size=body.size,
            )
        )
        db.commit()

    # Size and type are signed: the store refuses anything else, so this is
    # enforced there too, not only here (D38).
    url = store.presign(
        "PUT",
        key,
        UPLOAD_URL_SECONDS,
        headers={"Content-Type": body.type, "Content-Length": str(body.size)},
    )
    return NewUploadOut(file_id=upload_id, url=url, content_type=body.type)


@router.post("/files", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_file(chat_id: uuid.UUID, body: SendFileRequest, response: Response, me: User = Depends(get_current_user)):
    """Save the file's message, now that the upload is finished (D9)."""
    _store_ready()
    # The same limit as a text: it is one message.
    limits.enforce(limits.SEND, me.id)
    with SessionLocal() as db:
        _member_or_404(db, chat_id, me)
        upload = db.get(Upload, body.file_id)
        # Only my own upload, for this same chat.
        if upload is None or upload.user_id != me.id or upload.chat_id != chat_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
        key, name, content_type, size = upload.key, upload.name, upload.content_type, upload.size
        attached = upload.message_id is not None

    # A retry of a send that was saved skips this: save_and_push returns the first copy.
    if not attached:
        # Outside the session, so a slow store can't hold a connection (D34).
        try:
            stored = store.head(key)
        except StoreError:
            raise _store_failed() from None
        if stored is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "The upload hasn't finished")
        # The store's own numbers, never what the app says it sent.
        if stored.size != size or stored.size > MAX_FILE_BYTES or stored.content_type != content_type:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The file doesn't match its upload")

    category = ALLOWED_TYPES[content_type]
    data: dict = {
        "file_id": str(body.file_id),
        "name": name,
        "type": content_type,
        "size": size,
        "category": category,
    }
    if category == "image":
        data |= {"width": body.width, "height": body.height, "preview": body.preview}
    if category == "voice":
        data["duration_ms"] = body.duration_ms

    return save_and_push(chat_id, me, response, body.client_msg_id, "", kind="file", data=data, upload_id=body.file_id)


@router.get("/files", response_model=FilePage)
def chat_files(
    chat_id: uuid.UUID,
    before: int | None = Query(default=None, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
    me: User = Depends(get_current_user),
):
    """The side panel's list: the files in the part of the chat I can see (D37)."""
    query = (
        select(Message, User.name)
        .join(User, User.id == Message.sender_id)
        .where(Message.chat_id == chat_id, Message.kind == "file", Message.deleted_at.is_(None))
        .order_by(Message.seq.desc())
    )
    if before is not None:
        query = query.where(Message.seq < before)
    with SessionLocal() as db:
        member = _member_or_404(db, chat_id, me)
        query = query.where(Message.seq >= member.from_seq)
        if not member.current:
            query = query.where(Message.seq <= member.until_seq)
        rows = list(db.execute(query.limit(limit + 1)))
        return FilePage(
            messages=[MessageOut.of(message, name) for message, name in rows[:limit]],
            has_more=len(rows) > limit,
        )


@router.get("/files/{file_id}/url", response_model=FileUrlOut)
def file_url(
    chat_id: uuid.UUID,
    file_id: uuid.UUID,
    # True: the browser saves the file instead of showing it.
    download: bool = False,
    me: User = Depends(get_current_user),
):
    """A short-lived link to one sent file, only for someone who may see it now."""
    _store_ready()
    limits.enforce(limits.FILE_URL, me.id)
    with SessionLocal() as db:
        member = _member_or_404(db, chat_id, me)
        row = db.execute(
            select(Upload.key, Upload.name, Upload.content_type, Message.seq)
            .join(Message, Message.id == Upload.message_id)
            .where(Upload.id == file_id, Upload.chat_id == chat_id)
        ).one_or_none()
        # Sent, and in my stretch of the chat: nothing from before I joined (D37).
        if row is None or row.seq < member.from_seq:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
        # Someone who left keeps what's already on their screen, but gets no
        # new links (the brief: current members only).
        if not member.current:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You're no longer a member of this group")

    query = {}
    # Documents are always saved, never opened on our own site.
    if download or ALLOWED_TYPES[row.content_type] == "document":
        query["response-content-disposition"] = f"attachment; filename*=UTF-8''{quote(row.name, safe='')}"
    url = store.presign("GET", row.key, DOWNLOAD_URL_SECONDS, query=query)
    return FileUrlOut(url=url, expires_in=DOWNLOAD_URL_SECONDS)
