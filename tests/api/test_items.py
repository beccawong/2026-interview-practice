from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient

ITEMS = "/api/v1/items"
WIDGET = {"name": "Widget", "description": "A widget", "price": "9.99"}


def _create(client: TestClient, **overrides: Any) -> dict[str, Any]:
    response = client.post(ITEMS, json=WIDGET | overrides)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_create_and_get_item(client: TestClient) -> None:
    created = _create(client)

    response = client.get(f"{ITEMS}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created
    assert created["price"] == "9.99"
    assert created["in_stock"] is True


def test_list_items_paginates(client: TestClient) -> None:
    for i in range(3):
        _create(client, name=f"Item {i}")

    response = client.get(ITEMS, params={"offset": 1, "limit": 1})

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Item 1"]


def test_replace_item(client: TestClient) -> None:
    created = _create(client)

    response = client.put(f"{ITEMS}/{created['id']}", json={"name": "Gadget", "price": "5.00"})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Gadget"
    assert body["description"] is None
    assert body["created_at"] == created["created_at"]


def test_patch_item_changes_only_given_fields(client: TestClient) -> None:
    created = _create(client)

    response = client.patch(f"{ITEMS}/{created['id']}", json={"in_stock": False})

    assert response.status_code == 200
    body = response.json()
    assert body["in_stock"] is False
    assert body["name"] == created["name"]
    assert body["updated_at"] >= created["updated_at"]


def test_patch_null_description_clears_it(client: TestClient) -> None:
    created = _create(client)

    response = client.patch(f"{ITEMS}/{created['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_patch_rejects_null_for_required_field(client: TestClient) -> None:
    created = _create(client)

    response = client.patch(f"{ITEMS}/{created['id']}", json={"name": None})

    assert response.status_code == 422


def test_delete_item(client: TestClient) -> None:
    created = _create(client)

    assert client.delete(f"{ITEMS}/{created['id']}").status_code == 204
    assert client.get(f"{ITEMS}/{created['id']}").status_code == 404


def test_missing_item_returns_404(client: TestClient) -> None:
    assert client.get(f"{ITEMS}/{uuid4()}").status_code == 404


def test_duplicate_name_returns_409(client: TestClient) -> None:
    _create(client)

    assert client.post(ITEMS, json=WIDGET).status_code == 409


def test_invalid_payload_returns_422(client: TestClient) -> None:
    assert client.post(ITEMS, json={"name": "", "price": "-1"}).status_code == 422
