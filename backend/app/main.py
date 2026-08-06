from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import User  # imports all mapped models through package initialization
from app.services.graph import graph_store
from app.services.search import search
from app.services.storage import storage


settings = get_settings()


def initialize_database() -> None:
    last_error: Exception | None = None
    for _ in range(30):
        try:
            with engine.begin() as connection:
                connection.execute(text("SELECT 1"))
            Base.metadata.create_all(bind=engine)
            with SessionLocal() as db:
                admin = db.scalar(select(User).where(User.email == settings.admin_email.casefold()))
                if not admin:
                    admin = User(
                        email=settings.admin_email.casefold(),
                        full_name=settings.admin_name,
                        password_hash=hash_password(settings.admin_password),
                        role="admin",
                        is_active=True,
                    )
                    db.add(admin)
                    db.commit()
            return
        except Exception as exc:  # pragma: no cover - startup retry path
            last_error = exc
            time.sleep(2)
    raise RuntimeError("Database initialization failed") from last_error


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    storage.ensure_buckets()
    try:
        search.ensure_index()
    except Exception:
        pass
    try:
        graph_store.verify()
    except Exception:
        pass
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Evidence-first cybercrime investigation platform MVP",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }
