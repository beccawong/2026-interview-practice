# item-api

Layered FastAPI + Pydantic v2 REST service. Python 3.13, managed with uv.

## Docs
- `ARCHITECTURE.md`: layers, import rules, API versioning, conventions, how to add a resource or
  version. Read it before adding files or changing structure.
- `STYLEGUIDE.md`: Python code style. Follow it for all code.

## Commands
- Run: `uv sync`, `uv run fastapi dev`, `uv run pytest`
- Must pass before finishing:
  `uv run ruff format . && uv run ruff check . && uv run mypy src tests && uv run lint-imports && uv run pytest`
- Dependencies: `uv add [--dev] <pkg>` only. Never use pip or hand-edit `uv.lock`.
