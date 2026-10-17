from collections.abc import Sequence
from uuid import UUID

from item_api.domain.errors import ConflictError, NotFoundError
from item_api.domain.item import Item, ItemCreate, ItemUpdate
from item_api.repositories.item import ItemRepository


class ItemService:
    """Item use cases. Owns business rules; knows nothing about HTTP."""

    def __init__(self, repository: ItemRepository) -> None:
        self._repository = repository

    def list_items(self, *, offset: int = 0, limit: int = 100) -> Sequence[Item]:
        return self._repository.list(offset=offset, limit=limit)

    def get_item(self, item_id: UUID) -> Item:
        item = self._repository.get(item_id)
        if item is None:
            raise NotFoundError("Item", item_id)
        return item

    def create_item(self, data: ItemCreate) -> Item:
        self._ensure_name_available(data.name)
        return self._repository.save(Item(**data.model_dump()))

    def replace_item(self, item_id: UUID, data: ItemCreate) -> Item:
        item = self.get_item(item_id)
        self._ensure_name_available(data.name, exclude_id=item_id)
        return self._repository.save(item.replace(data))

    def update_item(self, item_id: UUID, data: ItemUpdate) -> Item:
        item = self.get_item(item_id)
        if data.name is not None:
            self._ensure_name_available(data.name, exclude_id=item_id)
        return self._repository.save(item.update(data))

    def delete_item(self, item_id: UUID) -> None:
        if not self._repository.delete(item_id):
            raise NotFoundError("Item", item_id)

    def _ensure_name_available(self, name: str, *, exclude_id: UUID | None = None) -> None:
        existing = self._repository.get_by_name(name)
        if existing is not None and existing.id != exclude_id:
            raise ConflictError(f"Item named {name!r} already exists")
