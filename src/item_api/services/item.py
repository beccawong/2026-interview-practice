from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from item_api.crud import item as item_crud
from item_api.core.errors import ConflictError, NotFoundError
from item_api.models.item import Item
from item_api.services.unset import UNSET, Unset


@dataclass(frozen=True, kw_only=True)
class ItemInput:
    """Every client-settable Item field. Creates an Item, or fully replaces one."""

    name: str
    description: str | None
    price: Decimal
    in_stock: bool


@dataclass(frozen=True, kw_only=True)
class ItemChanges:
    """A partial update. Fields left as ``UNSET`` are not changed."""

    name: str | Unset = UNSET
    description: str | Unset | None = UNSET
    price: Decimal | Unset = UNSET
    in_stock: bool | Unset = UNSET


class ItemService:
    """Item use cases. Owns business rules; knows nothing about HTTP."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_items(self, *, offset: int = 0, limit: int = 100) -> Sequence[Item]:
        return item_crud.list_items(self._session, offset=offset, limit=limit)

    def get_item(self, item_id: UUID) -> Item:
        item = item_crud.get_item(self._session, item_id)
        if item is None:
            raise NotFoundError("Item", item_id)
        return item

    def create_item(self, data: ItemInput) -> Item:
        self._ensure_name_available(data.name)
        item = Item(
            name=data.name,
            description=data.description,
            price=data.price,
            in_stock=data.in_stock,
        )
        return item_crud.save_item(self._session, item)

    def replace_item(self, item_id: UUID, data: ItemInput) -> Item:
        item = self.get_item(item_id)
        self._ensure_name_available(data.name, exclude_id=item_id)
        item.name = data.name
        item.description = data.description
        item.price = data.price
        item.in_stock = data.in_stock
        return item_crud.save_item(self._session, item)

    def update_item(self, item_id: UUID, changes: ItemChanges) -> Item:
        item = self.get_item(item_id)
        if changes.name is not UNSET:
            self._ensure_name_available(changes.name, exclude_id=item_id)
            item.name = changes.name
        if changes.description is not UNSET:
            item.description = changes.description
        if changes.price is not UNSET:
            item.price = changes.price
        if changes.in_stock is not UNSET:
            item.in_stock = changes.in_stock
        return item_crud.save_item(self._session, item)

    def delete_item(self, item_id: UUID) -> None:
        item_crud.delete_item(self._session, self.get_item(item_id))

    def _ensure_name_available(self, name: str, *, exclude_id: UUID | None = None) -> None:
        existing = item_crud.get_item_by_name(self._session, name)
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(f"Item named {name!r} already exists")
