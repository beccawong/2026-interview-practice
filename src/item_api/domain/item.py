from datetime import UTC, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ItemFields(BaseModel):
    """Attributes a client may set on an Item, with their invariants."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    in_stock: bool = True


class ItemCreate(ItemFields):
    """Input for creating an Item, or fully replacing one (PUT)."""


class ItemUpdate(BaseModel):
    """Input for partially updating an Item (PATCH). Only fields that are set are applied."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    in_stock: bool | None = None

    @model_validator(mode="after")
    def _reject_null_for_required_fields(self) -> Self:
        nulled = {"name", "price", "in_stock"} & {
            field for field in self.model_fields_set if getattr(self, field) is None
        }
        if nulled:
            raise ValueError(f"fields cannot be null: {', '.join(sorted(nulled))}")
        return self


class Item(ItemFields):
    """The Item entity."""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    def replace(self, data: ItemCreate) -> Self:
        """Return a copy with every client-settable field replaced by ``data``."""
        return self._with(data.model_dump())

    def update(self, data: ItemUpdate) -> Self:
        """Return a copy with only the fields explicitly set in ``data`` changed."""
        return self._with(data.model_dump(exclude_unset=True))

    def _with(self, changes: dict[str, object]) -> Self:
        return self.model_copy(update=changes | {"updated_at": _utcnow()})
