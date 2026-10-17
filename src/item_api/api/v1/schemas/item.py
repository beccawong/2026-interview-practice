"""v1 request and response models, and their mapping to service inputs and models."""

from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from item_api.models.item import Item
from item_api.services.item import ItemChanges, ItemInput
from item_api.services.unset import UNSET


class ItemCreateRequest(BaseModel):
    """Body for POST (create) and PUT (full replace)."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    in_stock: bool = True

    def to_input(self) -> ItemInput:
        return ItemInput(
            name=self.name,
            description=self.description,
            price=self.price,
            in_stock=self.in_stock,
        )


class ItemUpdateRequest(BaseModel):
    """Body for PATCH. Only fields the client sent are changed."""

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

    def to_changes(self) -> ItemChanges:
        # name, price and in_stock reject null, so None means "not sent". description may be
        # set to null, so check whether it was sent.
        return ItemChanges(
            name=UNSET if self.name is None else self.name,
            description=self.description if "description" in self.model_fields_set else UNSET,
            price=UNSET if self.price is None else self.price,
            in_stock=UNSET if self.in_stock is None else self.in_stock,
        )


class ItemResponse(BaseModel):
    """Public representation of an Item. Decouples the wire format from the database model."""

    id: UUID
    name: str
    description: str | None
    price: Decimal
    in_stock: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, item: Item) -> Self:
        return cls(
            id=item.id,
            name=item.name,
            description=item.description,
            price=item.price,
            in_stock=item.in_stock,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
