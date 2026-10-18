from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from item_api.core.config import Settings
from item_api.core.database import create_db_engine
from item_api.main import create_app
from item_api.models import Base
from item_api.services.item import ItemService

IN_MEMORY_DB = "sqlite://"


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(Settings(database_url=IN_MEMORY_DB))) as test_client:
        yield test_client


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_db_engine(IN_MEMORY_DB)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


@pytest.fixture
def item_service(db_session: Session) -> ItemService:
    return ItemService(db_session)
