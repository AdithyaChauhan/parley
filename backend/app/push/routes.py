from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.models import User
from app.config import settings
from app.db import get_db
from app.limits import service as limits
from app.push.models import PushSubscription
from app.push.schemas import PublicKeyOut, SubscribeIn, UnsubscribeIn

router = APIRouter(prefix="/push", tags=["push"])


@router.get("/key", response_model=PublicKeyOut)
def public_key():
    # Public on purpose: it only lets a browser check that pushes came from us.
    if not settings.vapid_public_key:
        # No keys in .env: push can't work, so say so clearly (D26).
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Notifications unavailable")
    return PublicKeyOut(public_key=settings.vapid_public_key)


@router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def subscribe(body: SubscribeIn, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    limits.enforce(limits.PUSH_SUBSCRIBE, me.id)
    # An "upsert", in one statement: add this browser, or if its endpoint is
    # already here, move that row to me with the browser's current keys.
    # Someone else may have been logged in on this browser before (D26).
    # Two tabs subscribing at once still make one row, and never an error.
    db.execute(
        insert(PushSubscription)
        .values(user_id=me.id, endpoint=body.endpoint, p256dh=body.keys.p256dh, auth=body.keys.auth)
        .on_conflict_do_update(
            index_elements=[PushSubscription.endpoint],
            set_={"user_id": me.id, "p256dh": body.keys.p256dh, "auth": body.keys.auth},
        )
    )
    db.commit()


@router.delete("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(body: UnsubscribeIn, me: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Only my own row. Someone else's endpoint is left alone, with the same
    # 204, so the reply doesn't say whose browser it is.
    db.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == body.endpoint, PushSubscription.user_id == me.id
        )
    )
    db.commit()
