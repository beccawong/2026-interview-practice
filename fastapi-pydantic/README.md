# item-api

Layered FastAPI + Pydantic REST service for `Item`. See [ARCHITECTURE.md](ARCHITECTURE.md).

```bash
uv sync
uv run fastapi dev        # http://127.0.0.1:8000/docs
uv run pytest
```

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/items?offset=0&limit=100` | List items |
| GET | `/api/v1/items/{id}` | Get one item |
| POST | `/api/v1/items` | Create (201) |
| PUT | `/api/v1/items/{id}` | Replace |
| PATCH | `/api/v1/items/{id}` | Partial update |
| DELETE | `/api/v1/items/{id}` | Delete (204) |
| GET | `/api/health` | Health check (unversioned) |

Data is stored in SQLite (`item_api.db`). The schema is defined by the SQLAlchemy models in
[`models/`](src/item_api/models/). Delete `item_api.db` after changing
them. See ARCHITECTURE.md § Database.

Settings come from `ITEM_API_*` environment variables or `.env` (see `core/config.py`).
