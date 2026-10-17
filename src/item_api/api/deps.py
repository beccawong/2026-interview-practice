"""FastAPI dependency providers. The only place routes obtain services from."""

from typing import Annotated, cast

from fastapi import Depends, Request

from item_api.repositories.item import ItemRepository
from item_api.services.item import ItemService


def get_item_repository(request: Request) -> ItemRepository:
    return cast(ItemRepository, request.app.state.item_repository)


def get_item_service(
    repository: Annotated[ItemRepository, Depends(get_item_repository)],
) -> ItemService:
    return ItemService(repository)


ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
