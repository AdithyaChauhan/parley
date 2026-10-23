from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User, UserSession
from app.auth.schemas import LoginRequest, SignupRequest, TokenOut, UserOut
from app.auth.security import (
    REFRESH_TOKEN_DAYS,
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.db import get_db
from app.limits import service as limits

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
# The cookie is only sent to /api/auth/... routes, not to every API call.
REFRESH_COOKIE_PATH = "/api/auth"

# Checked against when the email doesn't exist, so a wrong email takes as
# long as a wrong password and the timing doesn't reveal which accounts exist.
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-password")


# --- Helpers ---


def _ip(request: Request) -> str:
    """Who is asking, for the per-IP limits (D24). Behind Nginx (T26) this is
    Nginx's own address, unless uvicorn runs with --proxy-headers trusting it."""
    return request.client.host if request.client else "unknown"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=REFRESH_TOKEN_DAYS * 24 * 60 * 60,
        httponly=True,  # the page's JavaScript can't read it
        samesite="lax",  # not sent when another site posts to us
        path=REFRESH_COOKIE_PATH,
        secure=False,  # local http for now; turned on in production
    )


def _start_session(db: Session, user: User, response: Response) -> TokenOut:
    """Add a sessions row, put the refresh token in a cookie, return an access token."""
    refresh_token = new_refresh_token()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS),
    )
    db.add(session)
    db.commit()

    _set_refresh_cookie(response, refresh_token)
    return TokenOut(access_token=create_access_token(user.id, session.id))


def _find_session(
    db: Session, refresh_token: str | None, lock: bool = False
) -> UserSession | None:
    """lock=True also locks the row until we commit (SELECT ... FOR UPDATE).
    Another request for the same row waits, then reads the saved version."""
    if not refresh_token:
        return None
    query = select(UserSession).where(
        UserSession.refresh_token_hash == hash_refresh_token(refresh_token)
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


# --- Routes ---


@router.post("/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    limits.enforce(limits.SIGNUP_IP, _ip(request))

    user = User(name=body.name, email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # The UNIQUE rule on users.email refused the row: the email is taken.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    return _start_session(db, user, response)


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    # Both counted before the password is checked (D24): a locked email is
    # refused even with the right password, and never costs a slow hash check.
    limits.enforce(limits.LOGIN_IP, _ip(request))
    limits.enforce(limits.LOGIN_EMAIL, body.email)

    user = db.scalar(select(User).where(User.email == body.email))

    password_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
    if not verify_password(body.password, password_hash) or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")

    # A good log-in: this email's count starts again from 0, so only
    # failures since the last good log-in count.
    limits.clear(limits.key(limits.LOGIN_EMAIL, body.email))
    return _start_session(db, user, response)


@router.post("/refresh", response_model=TokenOut)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: Session = Depends(get_db),
):
    # Locked: if two refreshes bring the same cookie at once, the second waits.
    # By then the first has saved a new fingerprint, so the old cookie no
    # longer matches and the second gets 401 instead of rotating it again.
    session = _find_session(db, refresh_token, lock=True)
    now = datetime.now(timezone.utc)
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired, please log in again")

    # Rotate: a new refresh token replaces the old one in the same row,
    # so the old one stops matching anything.
    new_token = new_refresh_token()
    session.refresh_token_hash = hash_refresh_token(new_token)
    session.expires_at = now + timedelta(days=REFRESH_TOKEN_DAYS)
    db.commit()

    _set_refresh_cookie(response, new_token)
    return TokenOut(access_token=create_access_token(session.user_id, session.id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: Session = Depends(get_db),
):
    session = _find_session(db, refresh_token)
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()

    # Must use the same path as when it was set, or the browser keeps it.
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, httponly=True, samesite="lax")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
