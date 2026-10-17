"""API version 1. Owns its routes and schemas; shares deps and error mapping with other versions."""

from fastapi import APIRouter

from item_api.api.v1.routes import items

router = APIRouter(prefix="/v1")
router.include_router(items.router)
