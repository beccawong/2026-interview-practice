from decimal import Decimal
from uuid import uuid4

import pytest

from item_api.core.errors import ConflictError, NotFoundError
from item_api.services.item import ItemChanges, ItemInput, ItemService

WIDGET = ItemInput(name="Widget", description="A widget", price=Decimal("1.00"), in_stock=True)


def test_create_item_rejects_duplicate_name(item_service: ItemService) -> None:
    item_service.create_item(WIDGET)

    with pytest.raises(ConflictError):
        item_service.create_item(WIDGET)


def test_update_item_allows_keeping_own_name(item_service: ItemService) -> None:
    item = item_service.create_item(WIDGET)

    updated = item_service.update_item(item.id, ItemChanges(name="Widget", price=Decimal("3.00")))

    assert updated.price == Decimal("3.00")


def test_update_item_leaves_unset_fields_alone(item_service: ItemService) -> None:
    item = item_service.create_item(WIDGET)

    updated = item_service.update_item(item.id, ItemChanges(in_stock=False))

    assert updated.in_stock is False
    assert (updated.name, updated.description, updated.price) == (
        "Widget",
        "A widget",
        Decimal("1.00"),
    )


def test_update_item_can_clear_description(item_service: ItemService) -> None:
    item = item_service.create_item(WIDGET)

    updated = item_service.update_item(item.id, ItemChanges(description=None))

    assert updated.description is None


def test_get_missing_item_raises_not_found(item_service: ItemService) -> None:
    with pytest.raises(NotFoundError):
        item_service.get_item(uuid4())


def test_delete_missing_item_raises_not_found(item_service: ItemService) -> None:
    with pytest.raises(NotFoundError):
        item_service.delete_item(uuid4())
