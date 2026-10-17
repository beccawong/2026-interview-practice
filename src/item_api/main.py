"""Composition root: builds the app, creates the database tables, and wires the session factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from item_api.api import health, v1
from item_api.api.errors import register_exception_handlers
from item_api.core.config import Settings, get_settings
from item_api.core.database import create_db_engine
from item_api.models import Base


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = create_db_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(engine)  # creates missing tables; never alters existing ones
        yield
        engine.dispose()

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    app.state.session_factory = sessionmaker(engine, expire_on_commit=False)
    register_exception_handlers(app)
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(v1.router, prefix=settings.api_prefix)
    return app


app = create_app()


def run() -> None:
    uvicorn.run("item_api.main:app", reload=get_settings().debug)
