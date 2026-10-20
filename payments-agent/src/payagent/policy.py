"""Guardrails. Every transfer, from a human or the agent, is checked here first."""

from datetime import UTC, datetime
from decimal import Decimal

from payagent.ledger import Ledger
from payagent.money import fmt

APPROVAL_THRESHOLD = Decimal("500.00")
DAILY_LIMIT = Decimal("1000.00")


class PolicyError(Exception):
    """A transfer was blocked by a guardrail."""


def today() -> str:
    return datetime.now(UTC).date().isoformat()


def spent_today(ledger: Ledger, account: str) -> Decimal:
    day = today()
    return sum(
        (e["amount"] for e in ledger.audit if e["from"] == account and e["at"] == day),
        Decimal("0"),
    )


def check(ledger: Ledger, src: str, amount: Decimal) -> None:
    """Raise PolicyError if this transfer must not happen at all."""
    spent = spent_today(ledger, src)
    if spent + amount > DAILY_LIMIT:
        raise PolicyError(
            f"daily limit exceeded for '{src}': {fmt(spent)} already sent today, "
            f"limit is {fmt(DAILY_LIMIT)}"
        )


def needs_approval(amount: Decimal) -> bool:
    return amount > APPROVAL_THRESHOLD
