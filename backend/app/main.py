"""SoleMate API entry point.

Run locally with ``uvicorn app.main:app --reload`` from the ``backend`` directory.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import catalog, orders, profiles, scans, site, stripe_webhook
from .config import get_settings
from .database import get_engine, init_db
from sqlmodel import Session
from .services.retention import purge_stale

log = logging.getLogger('solemate')


def _purge_once() -> None:
    try:
        with Session(get_engine()) as db:
            purge_stale(db)
    except Exception:  # never let housekeeping take the API down
        log.exception("retention purge failed")


async def _purge_loop() -> None:
    while True:
        await asyncio.to_thread(_purge_once)
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    task = asyncio.create_task(_purge_loop())
    try:
        yield
    finally:
        task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(scans.router)
    app.include_router(profiles.router)
    app.include_router(catalog.router)
    app.include_router(orders.router)
    app.include_router(stripe_webhook.router)
    app.include_router(site.router)

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name, "version": settings.version}

    return app


app = create_app()
