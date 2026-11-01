import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import APIRouter, Depends, FastAPI, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app import metrics
from app.auth.routes import router as auth_router
from app.chats.routes import router as chats_router
from app.config import settings
from app.db import get_db
from app.live import bus
from app.live.routes import router as live_router
from app.messages.routes import router as messages_router
from app.presence import service as presence
from app.push.routes import router as push_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts (before yield) and once when it stops.
    # The live line's Redis client is made here, inside the server's own event
    # loop, and closed on the way out (D22).
    presence.start()
    # The radio (D23): its listener runs in the background for the copy's
    # whole life, handing what it hears to this copy's own lines.
    await bus.start()
    listener = asyncio.create_task(bus.listen())
    yield
    listener.cancel()
    with suppress(asyncio.CancelledError):
        await listener
    await bus.stop()
    await presence.stop()


app = FastAPI(title="Parley", lifespan=lifespan)

# Every HTTP request passes through this on its way in and out: it times the
# request and counts it by route template and status (D32).
app.middleware("http")(metrics.measure)


# What Prometheus reads every 15 s: every number, as plain text. On the app
# itself, outside /api on purpose: Nginx passes on only /api/, so Prometheus
# (inside Parley's network) can read it and the internet can't (D32).
# async: it runs on the event loop, where live lines open and close, so it
# never counts the switchboard halfway through a change.
@app.get("/metrics", include_in_schema=False)
async def metrics_page():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Every backend route lives under /api (D17). The browser sees one site, and
# Vite (later Nginx) passes anything starting with /api on to this app.
api = APIRouter(prefix="/api")


@api.get("/health")
def health():
    return {"status": "ok", "copy": settings.copy_name, "version": settings.app_version}


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
api.include_router(push_router)
# Last, after every route above is added to the /api router.
app.include_router(api)
