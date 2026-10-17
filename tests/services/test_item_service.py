from decimal import Decimal
from uuid import uuid4

import pytest

from item_api.domain.errors import ConflictError, NotFoundError
from item_api.domain.item import ItemCreate, ItemUpdate
from item_api.services.item import ItemService


def test_create_item_rejects_duplicate_name(item_service: ItemService) -> None:
    item_service.create_item(ItemCreate(name="Widget", price=Decimal("1.00")))

    with pytest.raises(ConflictError):
        item_service.create_item(ItemCreate(name="Widget", price=Decimal("2.00")))


def test_update_item_allows_keeping_own_name(item_service: ItemService) -> None:
    item = item_service.create_item(ItemCreate(name="Widget", price=Decimal("1.00")))

    updated = item_service.update_item(item.id, ItemUpdate(name="Widget", price=Decimal("3.00")))

    assert updated.price == Decimal("3.00")


def test_get_missing_item_raises_not_found(item_service: ItemService) -> None:
    with pytest.raises(NotFoundError):
        item_service.get_item(uuid4())


def test_delete_missing_item_raises_not_found(item_service: ItemService) -> None:
    with pytest.raises(NotFoundError):
        item_service.delete_item(uuid4())
