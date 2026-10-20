from dataclasses import dataclass, field
from decimal import Decimal

from payagent.money import fmt

FEES_ACCOUNT = "fees"


class LedgerError(Exception):
    """A transfer could not be applied to the books."""


@dataclass
class Ledger:
    accounts: dict[str, Decimal]
    audit: list[dict] = field(default_factory=list)
    approvals: list[dict] = field(default_factory=list)
    idempotency: dict[str, dict] = field(default_factory=dict)

    def balance(self, account: str) -> Decimal:
        try:
            return self.accounts[account]
        except KeyError:
            raise LedgerError(f"unknown account '{account}'") from None

    def move(self, src: str, dst: str, amount: Decimal, fee: Decimal) -> None:
        """Debit amount + fee from src. Credit amount to dst and the fee to the fees account."""
        total = amount + fee
        available = self.balance(src)
        if available < total:
            raise LedgerError(f"insufficient funds in '{src}': need {fmt(total)}, have {fmt(available)}")
        self.accounts[src] -= total
        self.accounts[dst] = self.balance(dst) + amount
        self.accounts[FEES_ACCOUNT] += fee
