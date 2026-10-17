from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from item_api.main import create_app
from item_api.repositories.item import InMemoryItemRepository
from item_api.services.item import ItemService


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def item_service() -> ItemService:
    return ItemService(InMemoryItemRepository())
