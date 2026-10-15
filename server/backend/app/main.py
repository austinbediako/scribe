from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.actions import router as actions_router
from app.api.routes.auth import router as auth_router
from app.api.routes.calendars import router as calendars_router
from app.api.routes.captures import router as captures_router
from app.api.routes.health import router as health_router
from app.api.routes.insights import router as insights_router
from app.api.routes.meetings import router as meetings_router
from app.api.routes.sync import router as sync_router
from app.api.routes.websocket import router as websocket_router
from app.core.config import settings
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(captures_router)
app.include_router(calendars_router)
app.include_router(meetings_router)
app.include_router(sync_router)
app.include_router(insights_router)
app.include_router(actions_router)
app.include_router(websocket_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"app": settings.app_name, "environment": settings.environment}
