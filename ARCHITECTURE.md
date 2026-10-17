# Architecture

`item-api` is a layered FastAPI service backed by SQLite. Each layer is a subpackage of
`src/item_api/`, and **imports only flow downward**. A lower layer never imports a higher one.

```
            ┌───────────────────────────────┐
            │ main.py   (composition root)  │  builds the app, creates tables, wires the DB
            └──────────────┬────────────────┘
                           ▼
            ┌───────────────────────────────┐
            │ api/      (presentation)      │  HTTP: versioned routes + schemas, DI, error mapping
            └──────────────┬────────────────┘
                           ▼
            ┌───────────────────────────────┐
            │ services/ (application)       │  use cases and business rules
            └──────────────┬────────────────┘
                           ▼
            ┌───────────────────────────────┐
            │ crud/     (data access)       │  database queries, one module per model
            └──────────────┬────────────────┘
                           ▼
            ┌──────────────┴┬───────────────┐
            │ models/       │ domain/       │  models: SQLAlchemy tables (the schema)
            │               │               │  domain: domain errors
            └───────────────┴───────────────┘

  core/  (config, database engine) is cross-cutting: any layer may import it; it imports no
  other layer. models/ and domain/ are independent of each other.
```

## Layers

| Directory | Responsibility | May import | Must not import |
|---|---|---|---|
| `main.py` | Create the `FastAPI` app, create missing tables on startup, put the session factory on `app.state`, register routers and error handlers. | everything | — |
| `api/` | Translate HTTP ⇄ application calls, **including all mapping between wire formats and the inner layers**. `v<N>/routes/` (one module per resource), `v<N>/schemas/` (request and response models with their mapping methods), plus version-independent `deps.py` (session + service providers), `errors.py` (domain error → status code), `health.py`. | `services`, `models`, `domain`, `core` | `main`; one `v<N>` must not import another |
| `services/` | Use cases (`ItemService`) and their plain-dataclass inputs (`ItemInput`, `ItemChanges`). Enforce business rules such as unique names, and copy inputs onto models field by field. Raise domain errors, never `HTTPException`. | `crud`, `models`, `domain`, `core` | `api`, `main`, `fastapi`, `starlette` |
| `crud/` | Database queries as plain functions that take a `Session` and work on models (`crud/item.py`: `get_item`, `save_item`, …). Write functions commit. No business rules. | `models`, `domain`, `core` | `services`, `api`, `main`, `fastapi`, `starlette` |
| `models/` | SQLAlchemy models. **This is the database schema**: each class is a table. `base.py` holds `Base` and shared column types. | `core` | every other layer, `fastapi`, `starlette` |
| `domain/` | The `DomainError` hierarchy (`domain/errors.py`). | `core` | every other layer, `fastapi`, `starlette` |
| `core/` | Settings (`config.py`) and the SQLite engine (`database.py`). | stdlib / third-party | any layer |

## Why one-way dependencies

- **Testable core.** Services are tested directly against an in-memory SQLite session, with no
  HTTP client (`tests/services/`). The API is tested end to end through `TestClient` (`tests/api/`).
- **No HTTP leakage.** Inner layers raise `NotFoundError` / `ConflictError`;
  `api/errors.py` alone decides these become 404 / 409.
- **Queries in one place.** Services decide *what* should happen; `crud/` is the only code that
  builds SQL, so a schema change touches `models/` and `crud/` only.

## Models: where each class lives

| Class | Location | Kind | Purpose |
|---|---|---|---|
| `ItemCreateRequest` | `api/v1/schemas/item.py` | Pydantic | Body for POST and PUT, with field validation. `to_input()` maps it to `ItemInput`. |
| `ItemUpdateRequest` | `api/v1/schemas/item.py` | Pydantic | Body for PATCH. `to_changes()` maps the fields the client sent to `ItemChanges`. |
| `ItemResponse` | `api/v1/schemas/item.py` | Pydantic | v1 wire format. `from_model()` builds it from the `Item` model. |
| `ItemInput` | `services/item.py` | dataclass | Service input for create / full replace: every client-settable field. |
| `ItemChanges` | `services/item.py` | dataclass | Service input for a partial update. Fields left as `UNSET` (`services/unset.py`) are not changed, so `None` can still mean "clear this field". |
| `Item` | `models/item.py` | SQLAlchemy | The entity and the `items` table. |

### No coupling between the API and the database

Each boundary is mapped explicitly, field by field. Nothing copies fields by name
(`**model_dump()`, `setattr`, `from_attributes`), so the wire format and the table can change
independently and mypy flags any mapping a rename breaks:

```
request JSON ─▶ ItemCreateRequest ─to_input()─▶ ItemInput ─service─▶ Item (model) ─crud─▶ DB
response JSON ◀─ ItemResponse ◀─from_model()─ Item (model)
```

- Rename a column: change `models/`, the service's assignments and `ItemResponse.from_model()`.
  The API is unchanged.
- Change the API (e.g. in `v2`): add new request/response models in `api/v2/schemas/` that map to
  the same service inputs. Services, crud and models are unchanged.

## API versioning

The URL version mirrors the directory: `/api/v1/items` lives in `api/v1/routes/items.py`.

```
api/
├── deps.py, errors.py, health.py   # shared by all versions; health is unversioned (/api/health)
└── v1/
    ├── __init__.py                 # router = APIRouter(prefix="/v1")
    ├── routes/items.py
    └── schemas/item.py
```

`main.py` mounts each `v<N>.router` under `settings.api_prefix` (`/api`).

Only the HTTP contract is versioned. Every version calls the same `services/`, which work on the
same service inputs and models. A version adapts its own schemas to those, so breaking changes stay inside
`api/v<N>/`. Versions never import each other, so an old version can be deleted on its own.

Adding v2:
1. Create `api/v2/` the same way as `v1/`, with only the routes and schemas that change.
2. Mount `v2.router` in `main.py`. To carry an unchanged endpoint forward, include v1's route
   module under the `/v2` prefix there too. `main.py` may import both versions; `v2` itself may not import `v1`.
3. Add `"item_api.api.v2"` to the independence contract in `pyproject.toml`.

## Database

SQLite through SQLAlchemy 2.x (sync). Set the database with `ITEM_API_DATABASE_URL` (default:
`sqlite:///./item_api.db`; tests use in-memory `sqlite://`).

- **`models/` is the schema.** Define tables there only, one module per model, and export each
  model from `models/__init__.py` so it is registered on `Base.metadata`. On startup, `main.py`
  runs `Base.metadata.create_all()`, which creates missing tables but never alters existing ones. There are no migrations: after changing a model, delete `item_api.db`.
  To see the SQL it generates, run `sqlite3 item_api.db .schema`.
- **Foreign keys are on.** SQLite ignores them by default; `core/database.py` runs
  `PRAGMA foreign_keys = ON` on each connection.
- **Sessions:** `api/deps.py` opens one `Session` per request (`SessionDep`) and passes it to the
  service. `crud/` write functions commit.
- **Type notes:** UUIDs are stored as 32 hex characters (`CHAR(32)`), and datetimes as naive UTC
  (`UTCDateTime` in `models/base.py` turns them back into aware datetimes on load). `id`,
  `created_at` and `updated_at` are filled in by column defaults; `updated_at` also has `onupdate`.

## Request flow (`PATCH /api/v1/items/{id}`)

1. `api/v1/routes/items.py` – FastAPI validates the body into `ItemUpdateRequest`, and `ItemServiceDep` resolves the service. The route calls `payload.to_changes()`.
2. `api/deps.py` – opens a `Session` and builds `ItemService` with it.
3. `services/item.py` – loads the item, checks the name is still unique, and sets every field that is not `UNSET` on the model.
4. `crud/item.py` – `save_item` commits (`updated_at` bumps via `onupdate`).
5. The route returns `ItemResponse.from_model(item)`. A `DomainError` raised along the way is turned into JSON by `api/errors.py`.

## Conventions

- **Errors:** below `api/`, raise `DomainError` subclasses (`domain/errors.py`), never `HTTPException`.
  `api/errors.py` maps them to status codes.
- **Data access:** only `crud/` runs queries. Services call crud functions, never `session.execute`.
- **Thin routes:** a route validates input, maps it with the request model's `to_*()` method,
  calls one service method, and returns `<Entity>Response.from_model(...)`.
- **Explicit mapping:** never copy fields between layers by name (`**model_dump()`, `setattr`
  loops, `from_attributes`). Write each field out.
- **PUT vs PATCH:** PUT replaces every client-settable field (`ItemCreateRequest` → `ItemInput`).
  PATCH applies only the fields the client sent (`ItemUpdateRequest` → `ItemChanges`).
- **Naming:** entity modules are singular (`models/item.py`, `crud/item.py`, `services/item.py`); route modules are
  plural after the URL (`api/v1/routes/items.py`); service methods and crud functions are
  `<verb>_<entity>` (`create_item`); request models are
  `<Entity><Create|Update>Request`; response models are `<Entity>Response`; service inputs are
  `<Entity>Input` / `<Entity>Changes`.
- **Tests:** every test gets a fresh in-memory SQLite database. `tests/services/` uses the
  `item_service` fixture, `tests/crud/` the `db_session` fixture, and `tests/api/` the `client`
  fixture. New behavior gets a test in both services and api.

## Enforcement

`import-linter` checks these rules (see `[tool.importlinter]` in `pyproject.toml`):

```bash
uv run lint-imports
```

- **layers** contract: `main → api → services → crud → (models | domain)`.
- **forbidden** contract: `services`, `crud`, `models`, `domain` may not import `fastapi` or `starlette`.
- **independence** contract: `api.v1`, `api.v2`, … may not import each other (list each version).

## Adding a new resource (e.g. `Order`)

Add the files from the bottom layer up, so each one only imports files that already exist:

1. `models/order.py` – `Order` SQLAlchemy model; export it from `models/__init__.py`
2. `crud/order.py` – query functions
3. `services/order.py` – `OrderInput`, `OrderChanges`, `OrderService`
4. `api/v1/schemas/order.py` – `OrderCreateRequest`, `OrderUpdateRequest`, `OrderResponse` with
   their mapping methods
5. `api/deps.py` – `get_order_service`, `OrderServiceDep`
6. `api/v1/routes/orders.py` – `router`, then include it in `api/v1/__init__.py`
7. `tests/services/test_order_service.py`, `tests/crud/test_order_crud.py`, `tests/api/test_orders.py`
8. Delete `item_api.db` so the new table is created on the next start.
