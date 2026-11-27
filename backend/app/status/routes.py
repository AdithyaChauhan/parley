import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app import busy
from app.auth.deps import get_current_user
from app.auth.models import User
from app.db import SessionLocal
from app.files.s3 import StoreError
from app.files.store import ALLOWED_TYPES, DOWNLOAD_URL_SECONDS, UPLOAD_URL_SECONDS, configured, store
from app.limits import service as limits
from app.live import bus
from app.status import cleanup
from app.status.models import Status, StatusView
from app.status.schemas import (
    PersonStatuses,
    PostStatusRequest,
    StatusEvent,
    StatusFeed,
    StatusOut,
    StatusUploadOut,
    StatusUploadRequest,
    StatusUrlOut,
    ViewerOut,
)
from app.status.service import LIFETIME, audience, can_see, now, status_key

router = APIRouter(prefix="/status", tags=["status"])

NOT_FOUND = "Status not found"


def _push(people: list[uuid.UUID], owner_id: uuid.UUID, change: StatusEvent) -> None:
    """Tells apps that someone's statuses changed. They load the list again,
    so the event carries no status itself (D41)."""
    bus.publish(people, {"type": "status", "data": {"user_id": str(owner_id), "change": change}})


def _store_ready() -> None:
    if not configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "File storage isn't set up")


def _view_count(db, status_id: uuid.UUID) -> int:
    return db.scalar(select(func.count()).where(StatusView.status_id == status_id)) or 0


@router.get("", response_model=StatusFeed)
def feed(me: User = Depends(get_current_user)):
    """My statuses, and my people's, that haven't run out."""
    with SessionLocal() as db:
        people = audience(db, me.id)
        rows = db.scalars(
            select(Status)
            .where(
                Status.user_id.in_([me.id, *people]),
                Status.posted_at.is_not(None),
                Status.expires_at > now(),
            )
            .order_by(Status.posted_at)
        ).all()
        ids = [row.id for row in rows]
        seen = set(
            db.scalars(select(StatusView.status_id).where(StatusView.viewer_id == me.id, StatusView.status_id.in_(ids)))
        )
        mine = [row.id for row in rows if row.user_id == me.id]
        counts = dict(
            db.execute(
                select(StatusView.status_id, func.count())
                .where(StatusView.status_id.in_(mine))
                .group_by(StatusView.status_id)
            ).all()
        )

    by_person: dict[uuid.UUID, list[StatusOut]] = {}
    my_statuses = []
    for row in rows:
        if row.user_id == me.id:
            my_statuses.append(StatusOut.of(row, viewed=True, views=counts.get(row.id, 0)))
        else:
            by_person.setdefault(row.user_id, []).append(StatusOut.of(row, viewed=row.id in seen))

    groups = [
        PersonStatuses(
            user_id=user_id,
            name=people[user_id],
            statuses=statuses,
            all_viewed=all(s.viewed for s in statuses),
        )
        for user_id, statuses in by_person.items()
    ]
    groups.sort(key=lambda person: person.statuses[-1].posted_at, reverse=True)
    return StatusFeed(mine=my_statuses, people=groups)


@router.post("/uploads", response_model=StatusUploadOut, status_code=status.HTTP_201_CREATED)
def new_upload(body: StatusUploadRequest, me: User = Depends(get_current_user)):
    """Permission to put one photo in the store. It isn't a status until it's
    posted, once the upload is done (D9)."""
    _store_ready()
    # The same limit as a chat file: it's one upload.
    limits.enforce(limits.UPLOAD, me.id)
    if ALLOWED_TYPES.get(body.type) != "image":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "A status can only be a photo or text")

    key = status_key(me.id, body.id)
    upload = {"key": key, "type": body.type, "size": body.size}
    with SessionLocal() as db:
        row = db.get(Status, body.id)
        if row is None:
            db.add(Status(id=body.id, user_id=me.id, kind="image", data=upload))
        elif row.user_id != me.id or row.kind != "image" or row.posted_at is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "This status already exists")
        else:
            # A retry, maybe of a different photo: its own size and type now.
            row.data = upload
        try:
            db.commit()
        except IntegrityError:
            # Someone took this id at the same moment.
            raise HTTPException(status.HTTP_409_CONFLICT, "This status already exists") from None

    # Size and type are signed, so the store refuses anything else (D38).
    url = store.presign("PUT", key, UPLOAD_URL_SECONDS, headers={"Content-Type": body.type, "Content-Length": str(body.size)})
    return StatusUploadOut(url=url, content_type=body.type)


@router.post("", response_model=StatusOut, status_code=status.HTTP_201_CREATED)
def post_status(body: PostStatusRequest, response: Response, me: User = Depends(get_current_user)):
    """Posts a text, or a photo whose upload is finished. A retry with the same
    id returns the first copy."""
    limits.enforce(limits.STATUS_POST, me.id)
    with SessionLocal() as db:
        row = db.get(Status, body.id)
        if row is not None and row.user_id != me.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "This status already exists")
        if row is not None and row.posted_at is not None:
            # Already posted: here it is again, and nobody is told twice.
            response.status_code = status.HTTP_200_OK
            return StatusOut.of(row, viewed=True, views=_view_count(db, row.id))
        if body.kind == "image" and row is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "The upload hasn't started")
        if body.kind == "text" and row is not None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "This id belongs to a photo")
        upload = dict(row.data) if row is not None else None

    if upload is not None:
        _store_ready()
        # Outside the session, so a slow store can't hold a connection (D34).
        try:
            stored = store.head(upload["key"])
        except StoreError:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, busy.DETAIL, headers=busy.retry_after()) from None
        if stored is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "The upload hasn't finished")
        # The store's own numbers, never what the app says it sent (D38).
        if stored.size != upload["size"] or stored.content_type != upload["type"]:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The photo doesn't match its upload")

    posted_at = now()
    with SessionLocal() as db:
        if upload is None:
            row = Status(id=body.id, user_id=me.id, kind="text", body=body.body, color=body.color)
            db.add(row)
        else:
            row = db.get(Status, body.id, with_for_update=True)
            if row.posted_at is not None:
                # Another copy of this post got here first while we checked the store.
                response.status_code = status.HTTP_200_OK
                return StatusOut.of(row, viewed=True, views=_view_count(db, row.id))
            row.body = body.body
            row.data = upload | {"width": body.width, "height": body.height, "preview": body.preview}
        row.posted_at = posted_at
        row.expires_at = posted_at + LIFETIME
        try:
            db.commit()
        except IntegrityError:
            # The same post arrived twice at once, and the other copy won.
            db.rollback()
            row = db.get(Status, body.id)
            if row is None or row.user_id != me.id:
                raise
            response.status_code = status.HTTP_200_OK
            return StatusOut.of(row, viewed=True, views=_view_count(db, row.id))
        posted = StatusOut.of(row, viewed=True, views=0)
        people = list(audience(db, me.id))

    # Saved first (D9), then everyone who can see it, and my other tabs.
    _push([me.id, *people], me.id, "new")
    return posted


def _visible(db, status_id: uuid.UUID, me: User) -> Status:
    # The same 404 for "no such status", "not yours to see" and "run out".
    row = db.get(Status, status_id)
    if not can_see(db, me.id, row):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return row


@router.post("/{status_id}/view", status_code=status.HTTP_204_NO_CONTENT)
def view(status_id: uuid.UUID, me: User = Depends(get_current_user)):
    """I watched this status. Seeing it again changes nothing."""
    limits.enforce(limits.STATUS_VIEW, me.id)
    with SessionLocal() as db:
        row = _visible(db, status_id, me)
        owner_id = row.user_id
        if owner_id == me.id:
            return  # my own views don't count
        added = db.execute(
            insert(StatusView)
            .values(status_id=status_id, viewer_id=me.id)
            .on_conflict_do_nothing()
            .returning(StatusView.viewer_id)
        ).first()
        db.commit()
    if added is not None:
        # The poster's "Viewed by" count goes up.
        _push([owner_id], owner_id, "viewed")


@router.get("/{status_id}/views", response_model=list[ViewerOut])
def viewers(status_id: uuid.UUID, me: User = Depends(get_current_user)):
    """Who saw my status, latest first. Only the poster may ask."""
    with SessionLocal() as db:
        row = _visible(db, status_id, me)
        if row.user_id != me.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
        rows = db.execute(
            select(StatusView.viewer_id, User.name, StatusView.viewed_at)
            .join(User, User.id == StatusView.viewer_id)
            .where(StatusView.status_id == status_id)
            .order_by(StatusView.viewed_at.desc())
        ).all()
    return [ViewerOut(user_id=r.viewer_id, name=r.name, viewed_at=r.viewed_at) for r in rows]


@router.get("/{status_id}/url", response_model=StatusUrlOut)
def photo_url(status_id: uuid.UUID, me: User = Depends(get_current_user)):
    """A short-lived link to a photo status, only for someone who may see it now."""
    _store_ready()
    limits.enforce(limits.FILE_URL, me.id)
    with SessionLocal() as db:
        row = _visible(db, status_id, me)
        if row.kind != "image":
            raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
        key = row.data["key"]
    url = store.presign("GET", key, DOWNLOAD_URL_SECONDS)
    return StatusUrlOut(url=url, expires_in=DOWNLOAD_URL_SECONDS)


@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_status(status_id: uuid.UUID, me: User = Depends(get_current_user)):
    """Takes my status down for everyone at once, photo included."""
    with SessionLocal() as db:
        row = db.get(Status, status_id)
        if row is None or row.user_id != me.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
        was_live = row.posted_at is not None and row.expires_at > now()
        # Run out from this moment: nobody can see it or get a link any more.
        # The row and its photo are removed below, or by the hourly job (cleanup.py).
        row.expires_at = now()
        if row.posted_at is None:
            row.posted_at = row.expires_at
        db.commit()
        people = list(audience(db, me.id))

    if was_live:
        _push([me.id, *people], me.id, "gone")
    cleanup.erase(status_id)
