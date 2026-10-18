import json
import os
from pathlib import Path

from python_cli.models import Expense

DEFAULT_PATH = Path.home() / ".expenses.json"


def get_path() -> Path:
    return Path(os.environ.get("EXPENSES_FILE", DEFAULT_PATH))


def load(path: Path) -> list[Expense]:
    try:
        with open(path) as f:
            return [Expense.from_dict(d) for d in json.load(f)]
    except FileNotFoundError:
        return []


def save(path: Path, expenses: list[Expense]) -> None:
    with open(path, "a") as f:
        json.dump([e.to_dict() for e in expenses], f, indent=2)
