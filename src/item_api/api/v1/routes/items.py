from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from item_api.api.deps import ItemServiceDep
from item_api.api.v1.schemas.item import ItemResponse
from item_api.domain.item import ItemCreate, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.get("")
def list_items(
    service: ItemServiceDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ItemResponse]:
    return [
        ItemResponse.model_validate(item) for item in service.list_items(offset=offset, limit=limit)
    ]


@router.get("/{item_id}")
def get_item(item_id: UUID, service: ItemServiceDep) -> ItemResponse:
    return ItemResponse.model_validate(service.get_item(item_id))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, service: ItemServiceDep) -> ItemResponse:
    return ItemResponse.model_validate(service.create_item(payload))


@router.put("/{item_id}")
def replace_item(item_id: UUID, payload: ItemCreate, service: ItemServiceDep) -> ItemResponse:
    return ItemResponse.model_validate(service.replace_item(item_id, payload))


@router.patch("/{item_id}")
def update_item(item_id: UUID, payload: ItemUpdate, service: ItemServiceDep) -> ItemResponse:
    return ItemResponse.model_validate(service.update_item(item_id, payload))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: UUID, service: ItemServiceDep) -> None:
    service.delete_item(item_id)
