import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.security import decode_access_token
from app.db import get_db

# Reads the "Authorization: Bearer <token>" header and adds the Authorize
# button to /docs. auto_error=False: if the header is missing we send our
# own 401 below, the same as for a bad token.
bearer_scheme = HTTPBearer(auto_error=False)


def _not_logged_in() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not logged in",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _not_logged_in()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        # Fake, changed or expired token, or a "sub" that isn't a valid id.
        raise _not_logged_in()

    user = db.get(User, user_id)
    if user is None:
        # The token is real, but the account was deleted since.
        raise _not_logged_in()
    return user
