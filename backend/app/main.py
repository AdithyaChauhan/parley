from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.auth.routes import router as auth_router
from app.db import get_db

app = FastAPI(title="Parley")

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
# Last, after every route above is added to the /api router.
app.include_router(api)
