from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth.routes import router as auth_router
from app.chats.routes import router as chats_router
from app.db import get_db
from app.live.routes import router as live_router
from app.messages.routes import router as messages_router
from app.presence import service as presence


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts (before yield) and once when it stops.
    # The live line's Redis client is made here, inside the server's own event
    # loop, and closed on the way out (D22).
    presence.start()
    yield
    await presence.stop()


app = FastAPI(title="Parley", lifespan=lifespan)

# Every backend route lives under /api (D17). The browser sees one site, and
# Vite (later Nginx) passes anything starting with /api on to this app.
api = APIRouter(prefix="/api")


@api.get("/health")
def health():
    return {"status": "ok"}


@api.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("select 1"))
    except OperationalError:
        # The database can't be reached: say so clearly instead of a bare 500 error.
        return JSONResponse(status_code=503, content={"database": "unavailable"})
    return {"database": "ok"}


api.include_router(auth_router)
api.include_router(chats_router)
api.include_router(messages_router)
api.include_router(live_router)
# Last, after every route above is added to the /api router.
app.include_router(api)
