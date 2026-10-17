from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from item_api.domain.item import Item


class ItemRepository(Protocol):
    """Persistence port for Items. Services depend on this, not on a concrete store."""

    def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[Item]: ...
    def get(self, item_id: UUID) -> Item | None: ...
    def get_by_name(self, name: str) -> Item | None: ...
    def save(self, item: Item) -> Item: ...
    def delete(self, item_id: UUID) -> bool: ...


class InMemoryItemRepository:
    """Dict-backed ItemRepository. Swap for a database-backed implementation later."""

    def __init__(self) -> None:
        self._items: dict[UUID, Item] = {}

    def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[Item]:
        return list(self._items.values())[offset : offset + limit]

    def get(self, item_id: UUID) -> Item | None:
        return self._items.get(item_id)

    def get_by_name(self, name: str) -> Item | None:
        return next((item for item in self._items.values() if item.name == name), None)

    def save(self, item: Item) -> Item:
        self._items[item.id] = item
        return item

    def delete(self, item_id: UUID) -> bool:
        return self._items.pop(item_id, None) is not None
