import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.files.schemas import MAX_PREVIEW_CHARS, PREVIEW
from app.files.store import MAX_FILE_BYTES
from app.status.models import Status

# Spaces at both ends are trimmed. A text status needs words; a photo's caption may be empty.
StatusText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=700)]

# The app has 6 background colors for text statuses, numbered 0-5.
COLORS = 6


# --- What comes in ---


class StatusUploadRequest(BaseModel):
    """Permission to upload a photo status. The id is made by the app and is
    also the status's id."""

    id: uuid.UUID
    type: str
    size: int = Field(ge=1, le=MAX_FILE_BYTES)


class PostStatusRequest(BaseModel):
    # Made by the app, once per status, and sent again on a retry (like D9).
    id: uuid.UUID
    kind: Literal["text", "image"]
    body: StatusText = ""
    color: int = Field(default=0, ge=0, lt=COLORS)
    # Photos only, measured by the browser.
    width: int | None = Field(default=None, ge=1, le=30_000)
    height: int | None = Field(default=None, ge=1, le=30_000)
    preview: str | None = Field(default=None, max_length=MAX_PREVIEW_CHARS)

    @field_validator("preview")
    @classmethod
    def _image_data_only(cls, preview: str | None) -> str | None:
        if preview is not None and not PREVIEW.fullmatch(preview):
            raise ValueError("The preview must be a small JPEG")
        return preview

    @model_validator(mode="after")
    def _text_needs_words(self):
        if self.kind == "text" and not self.body:
            raise ValueError("A text status needs some text")
        return self


# --- What goes out ---


class StatusOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    kind: str
    body: str
    color: int
    # Photos only. The photo itself comes from GET /api/status/{id}/url.
    width: int | None
    height: int | None
    preview: str | None
    posted_at: datetime
    expires_at: datetime
    # Have I seen it? Always true for my own.
    viewed: bool
    # My own statuses only: how many people saw it. Null for other people's.
    views: int | None

    @classmethod
    def of(cls, status: Status, viewed: bool, views: int | None = None) -> "StatusOut":
        data = status.data or {}
        return cls(
            id=status.id,
            user_id=status.user_id,
            kind=status.kind,
            body=status.body,
            color=status.color,
            width=data.get("width"),
            height=data.get("height"),
            preview=data.get("preview"),
            posted_at=status.posted_at,
            expires_at=status.expires_at,
            viewed=viewed,
            views=views,
        )


class PersonStatuses(BaseModel):
    """One person's statuses, oldest first, the order they're watched in."""

    user_id: uuid.UUID
    name: str
    statuses: list[StatusOut]
    # Seen them all: the person moves to "Viewed updates", with a grey ring.
    all_viewed: bool


class StatusFeed(BaseModel):
    mine: list[StatusOut]
    # Newest status first.
    people: list[PersonStatuses]


class StatusUploadOut(BaseModel):
    # PUT the photo here, with exactly this Content-Type.
    url: str
    content_type: str


class ViewerOut(BaseModel):
    user_id: uuid.UUID
    name: str
    viewed_at: datetime


class StatusUrlOut(BaseModel):
    url: str
    expires_in: int


StatusEvent = Literal["new", "gone", "viewed"]
