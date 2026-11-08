import re
import uuid
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.files.store import MAX_FILE_BYTES, MAX_VOICE_MS
from app.messages.schemas import MessageOut

# A small picture made by the browser, as text: only image data, nothing that
# could run. About 40 px wide, so a few KB.
PREVIEW = re.compile(r"data:image/jpeg;base64,[A-Za-z0-9+/=]+")
MAX_PREVIEW_CHARS = 12_000


# --- What comes in ---


class NewUploadRequest(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    type: str
    size: int = Field(ge=1, le=MAX_FILE_BYTES)

    @field_validator("name")
    @classmethod
    def _plain_name(cls, name: str) -> str:
        # Just the last part of a path, without control characters.
        name = re.sub(r"[\x00-\x1f\x7f]", "", name.replace("\\", "/").rsplit("/", 1)[-1]).strip()
        if not name:
            raise ValueError("The file needs a name")
        return name


class SendFileRequest(BaseModel):
    client_msg_id: uuid.UUID
    file_id: uuid.UUID
    # Images only, measured by the browser.
    width: int | None = Field(default=None, ge=1, le=30_000)
    height: int | None = Field(default=None, ge=1, le=30_000)
    preview: str | None = Field(default=None, max_length=MAX_PREVIEW_CHARS)
    # Voice notes only.
    duration_ms: int | None = Field(default=None, ge=1, le=MAX_VOICE_MS)

    @field_validator("preview")
    @classmethod
    def _image_data_only(cls, preview: str | None) -> str | None:
        if preview is not None and not PREVIEW.fullmatch(preview):
            raise ValueError("The preview must be a small JPEG")
        return preview


# --- What goes out ---


class NewUploadOut(BaseModel):
    file_id: uuid.UUID
    # PUT the file here, with exactly this Content-Type.
    url: str
    content_type: str


class FileUrlOut(BaseModel):
    url: str
    expires_in: int


class FilePage(BaseModel):
    """The chat's files, newest first: messages of kind "file"."""

    messages: list[MessageOut]
    # Older ones are waiting: ask again with before=<smallest seq>.
    has_more: bool
