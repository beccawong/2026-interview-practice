from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ItemResponse(BaseModel):
    """Public representation of an Item. Decouples the wire format from the domain entity."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    price: Decimal
    in_stock: bool
    created_at: datetime
    updated_at: datetime
