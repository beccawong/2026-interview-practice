# Architecture

`item-api` is a layered FastAPI service. Each layer is a subpackage of `src/item_api/`, and
**imports only flow downward** (toward the domain). A lower layer never imports a higher one.

```
            ┌───────────────────────────────┐
            │ main.py   (composition root)  │  builds the app, picks concrete implementations
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
            │ repositories/ (persistence)   │  storage interface + implementations
            └──────────────┬────────────────┘
                           ▼
            ┌───────────────────────────────┐
            │ domain/   (core model)        │  entities, input models, invariants, errors
            └───────────────────────────────┘

  core/  (config) is cross-cutting: any layer may import it; it imports no other layer.
```

## Layers

| Directory | Responsibility | May import | Must not import |
|---|---|---|---|
| `main.py` | Create the `FastAPI` app, register routers and error handlers, wire concrete repositories into `app.state`. | everything | — |
| `api/` | Translate HTTP ⇄ application calls. `v<N>/routes/` (one module per resource), `v<N>/schemas/` (response models), plus version-independent `deps.py` (dependency providers), `errors.py` (domain error → status code), `health.py`. | `services`, `repositories` (types only, in `deps.py`), `domain`, `core` | `main`; one `v<N>` must not import another |
| `services/` | Use cases (`ItemService`). Enforce business rules such as unique names. Raise domain errors, never `HTTPException`. | `repositories`, `domain`, `core` | `api`, `main`, `fastapi`, `starlette` |
| `repositories/` | Persistence. `ItemRepository` is a `Protocol` (the port); `InMemoryItemRepository` is one implementation (the adapter). | `domain`, `core` | `services`, `api`, `main`, `fastapi`, `starlette` |
| `domain/` | Pydantic entity `Item`, input models `ItemCreate` / `ItemUpdate`, field invariants, `DomainError` hierarchy. Pure Python + Pydantic. | `core` (ideally nothing) | every other layer, `fastapi`, `starlette` |
| `core/` | Settings (`pydantic-settings`). | stdlib / third-party | any layer |

## Why one-way dependencies

- **Replaceable edges.** Swapping the in-memory store for Postgres means adding a new class in
  `repositories/` that satisfies `ItemRepository` and changing one line in `main.py`. Services
  and routes are untouched.
- **Testable core.** Services are tested with a plain repository, no HTTP client
  (`tests/services/`). The API is tested end to end through `TestClient` (`tests/api/`).
- **No HTTP leakage.** Inner layers raise `NotFoundError` / `ConflictError`;
  `api/errors.py` alone decides these become 404 / 409.

## Models: where each Pydantic class lives

| Model | Location | Purpose |
|---|---|---|
| `ItemCreate` | `domain/item.py` | Request body for POST and PUT; also the service input. |
| `ItemUpdate` | `domain/item.py` | Request body for PATCH; only fields the client sent (`exclude_unset`) are applied. |
| `Item` | `domain/item.py` | The entity, including `id` and timestamps. |
| `ItemResponse` | `api/v1/schemas/item.py` | v1 wire format returned to clients. Lets the entity change without breaking the API. |

Input models live in `domain/` because they carry the business invariants and the service
consumes them. If the request format ever has to differ from the service input, add request
schemas in `api/v<N>/schemas/` and map them to domain models in the route.

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
same `domain/` models. A version adapts its own schemas to those, so breaking changes stay inside
`api/v<N>/`. Versions never import each other, so an old version can be deleted on its own.

Adding v2:
1. Create `api/v2/` the same way as `v1/`, with only the routes and schemas that change.
2. Mount `v2.router` in `main.py`. To carry an unchanged endpoint forward, include v1's route
   module under the `/v2` prefix there too. `main.py` may import both versions; `v2` itself may not import `v1`.
3. Add `"item_api.api.v2"` to the independence contract in `pyproject.toml`.

## Request flow (`PATCH /api/v1/items/{id}`)

1. `api/v1/routes/items.py` – FastAPI validates the body into `ItemUpdate`, and `ItemServiceDep` resolves the service.
2. `api/deps.py` – builds `ItemService` with the repository from `app.state`.
3. `services/item.py` – loads the item, checks the name is still unique, calls `Item.update()`, saves.
4. `repositories/item.py` – stores the new `Item`.
5. The route returns `ItemResponse.model_validate(item)`. A `DomainError` raised along the way is turned into JSON by `api/errors.py`.

## Conventions

- **Errors:** below `api/`, raise `DomainError` subclasses (`domain/errors.py`), never `HTTPException`.
  `api/errors.py` maps them to status codes.
- **Wiring:** services depend on repository `Protocol`s. Only `main.py` picks the concrete class.
- **Thin routes:** a route validates input, calls one service method, and returns an
  `api/v<N>/schemas` response model.
- **PUT vs PATCH:** PUT replaces every client-settable field (`ItemCreate`). PATCH applies only the
  fields the client sent (`ItemUpdate`, `model_dump(exclude_unset=True)`).
- **Naming:** entity modules are singular (`domain/item.py`, `services/item.py`); route modules are
  plural after the URL (`api/v1/routes/items.py`); service methods are `<verb>_<entity>`
  (`create_item`); response models are `<Entity>Response`.
- **Tests:** `tests/services/` calls services directly with `InMemoryItemRepository`; `tests/api/` uses
  the `client` fixture (a fresh app per test). New behavior gets a test in both.

## Enforcement

`import-linter` checks these rules (see `[tool.importlinter]` in `pyproject.toml`):

```bash
uv run lint-imports
```

- **layers** contract: `main → api → services → repositories → domain`.
- **forbidden** contract: `services`, `repositories`, `domain` may not import `fastapi` or `starlette`.
- **independence** contract: `api.v1`, `api.v2`, … may not import each other (list each version).

## Adding a new resource (e.g. `Order`)

Add the files from the bottom layer up, so each one only imports files that already exist:

1. `domain/order.py` – `Order`, `OrderCreate`, `OrderUpdate`
2. `repositories/order.py` – `OrderRepository` Protocol + implementation
3. `services/order.py` – `OrderService`
4. `api/v1/schemas/order.py` – `OrderResponse`
5. `api/deps.py` – `get_order_service`, `OrderServiceDep`
6. `api/v1/routes/orders.py` – `router`, then include it in `api/v1/__init__.py`
7. `main.py` – wire the repository into `app.state`
8. `tests/services/test_order_service.py`, `tests/api/test_orders.py`
