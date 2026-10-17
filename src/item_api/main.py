"""Composition root: builds the app and wires concrete implementations into the layers."""

import uvicorn
from fastapi import FastAPI

from item_api.api import health, v1
from item_api.api.errors import register_exception_handlers
from item_api.core.config import Settings, get_settings
from item_api.repositories.item import InMemoryItemRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.state.item_repository = InMemoryItemRepository()
    register_exception_handlers(app)
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(v1.router, prefix=settings.api_prefix)
    return app


app = create_app()


def run() -> None:
    uvicorn.run("item_api.main:app", reload=get_settings().debug)
