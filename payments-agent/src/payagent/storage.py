import json
import os
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from payagent.ledger import Ledger, LedgerError

DEFAULT_PATH = Path.home() / ".payagent.json"
OPENING_BALANCES = {"ops": "5000.00", "acme": "0.00", "globex": "0.00", "fees": "0.00"}
AMOUNT_FIELDS = ("amount", "fee")


def get_path() -> Path:
    return Path(os.environ.get("PAYAGENT_FILE", DEFAULT_PATH))


def new_ledger() -> Ledger:
    return Ledger(accounts={name: Decimal(v) for name, v in OPENING_BALANCES.items()})


def _with_decimals(record: dict) -> dict:
    return {k: Decimal(v) if k in AMOUNT_FIELDS else v for k, v in record.items()}


def load(path: Path) -> Ledger:
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        raise LedgerError(f"no ledger at {path}. Run `payagent init` first.") from None
    return Ledger(
        accounts={name: Decimal(v) for name, v in data["accounts"].items()},
        audit=[_with_decimals(e) for e in data["audit"]],
        approvals=[_with_decimals(a) for a in data["approvals"]],
        idempotency=data["idempotency"],
    )


def save(path: Path, ledger: Ledger) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(asdict(ledger), f, indent=2, default=str)
    os.replace(tmp, path)
