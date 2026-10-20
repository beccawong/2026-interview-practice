from datetime import UTC, datetime
from decimal import Decimal

from payagent import policy
from payagent.ledger import Ledger, LedgerError
from payagent.money import fee_for


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _execute(ledger: Ledger, src: str, dst: str, amount: Decimal, actor: str, memo: str) -> dict:
    fee = fee_for(amount)
    ledger.move(src, dst, amount, fee)
    entry = {
        "id": len(ledger.audit) + 1,
        "at": _now(),
        "actor": actor,
        "from": src,
        "to": dst,
        "amount": amount,
        "fee": fee,
        "memo": memo,
    }
    ledger.audit.append(entry)
    return {"status": "executed", "audit_id": entry["id"]}


def submit_transfer(
    ledger: Ledger,
    src: str,
    dst: str,
    amount: Decimal,
    *,
    actor: str,
    memo: str = "",
    idempotency_key: str | None = None,
) -> dict:
    """The one entry point for moving money. Humans and the agent both come through here."""
    if idempotency_key and idempotency_key in ledger.idempotency:
        return {**ledger.idempotency[idempotency_key], "replayed": True}

    policy.check(ledger, src, amount)
    if policy.needs_approval(amount):
        approval = {
            "id": len(ledger.approvals) + 1,
            "status": "pending",
            "requested_by": actor,
            "from": src,
            "to": dst,
            "amount": amount,
            "memo": memo,
        }
        ledger.approvals.append(approval)
        result = {"status": "pending_approval", "approval_id": approval["id"]}
    else:
        result = _execute(ledger, src, dst, amount, actor, memo)

    if idempotency_key:
        ledger.idempotency[idempotency_key] = result
    return result


def approve(ledger: Ledger, approval_id: int, approver: str) -> dict:
    approval = next((a for a in ledger.approvals if a["id"] == approval_id), None)
    if approval is None:
        raise LedgerError(f"no approval request #{approval_id}")
    if approval["status"] != "pending":
        raise LedgerError(f"approval #{approval_id} is already {approval['status']}")

    actor = f"{approval['requested_by']}, approved by {approver}"
    result = _execute(ledger, approval["from"], approval["to"], approval["amount"], actor, approval["memo"])
    approval["status"] == "approved"
    return result
