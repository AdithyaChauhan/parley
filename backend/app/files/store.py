"""The one store this app talks to, built from settings (D29, D38), and the rules
for what may go in it."""

from typing import Literal

from app.config import settings
from app.files.s3 import Store

store = Store(
    endpoint=settings.storage_endpoint,
    public_url=settings.storage_public_url,
    bucket=settings.storage_bucket,
    region=settings.storage_region,
    access_key=settings.storage_access_key,
    secret_key=settings.storage_secret_key,
)

Category = Literal["image", "document", "voice"]

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB (D38)
MAX_VOICE_MS = 2 * 60 * 1000  # 2 minutes (D38)

# Long enough to start a slow upload: the store checks a URL when the request
# starts, so a transfer may run past this.
UPLOAD_URL_SECONDS = 5 * 60
# Short, and the app asks again when it's out of date.
DOWNLOAD_URL_SECONDS = 5 * 60

# The only types allowed, and what each one is (D38). HTML and SVG are left out
# on purpose: the store shares the app's site, so they could run scripts there.
ALLOWED_TYPES: dict[str, Category] = {
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
    "image/gif": "image",
    "application/pdf": "document",
    "text/plain": "document",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "document",
    "application/zip": "document",
    # What MediaRecorder makes: Chrome and Firefox, then iPhone Safari.
    "audio/webm": "voice",
    "audio/ogg": "voice",
    "audio/mp4": "voice",
}


def configured() -> bool:
    return bool(settings.storage_access_key and settings.storage_secret_key)


def file_key(chat_id: object, upload_id: object) -> str:
    """Made of ids only: a user's file name never touches a path."""
    return f"chats/{chat_id}/{upload_id}"
