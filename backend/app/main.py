from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .database import SessionLocal
from .migrate import migrate
from .routers import (
    ai_routes,
    auth,
    calls,
    chat,
    connections,
    consent,
    event_calls,
    events,
    feed,
    me,
    metrics,
    organizer,
    queries,
    wallet,
)
from .seed import seed_if_empty
from .seed_graph import seed_graph


@asynccontextmanager
async def lifespan(_: FastAPI):
    migrate()
    db = SessionLocal()
    try:
        seed_if_empty(db)
        seed_graph(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="MentorWow",
    description="Event-anchored professional networking graph.",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(metrics.router)
app.include_router(me.router)
app.include_router(feed.router)
app.include_router(wallet.router)
app.include_router(calls.router)
app.include_router(events.router)
app.include_router(queries.router)
app.include_router(event_calls.router)
app.include_router(chat.router)
app.include_router(connections.router)
app.include_router(organizer.router)
app.include_router(consent.router)
app.include_router(ai_routes.router)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "mentorwow"}


@app.post("/api/webhooks/linkedin")
def linkedin_webhook():
    return {"ok": True, "detail": "LinkedIn uses the OAuth callback. No webhook ingest."}
