import argparse
import csv
import json
import sys

from payagent import agent, service, storage
from payagent.ledger import Ledger, LedgerError
from payagent.money import fmt, parse_amount
from payagent.policy import PolicyError


def describe(result: dict) -> str:
    if result["status"] == "executed":
        text = f"executed (audit #{result['audit_id']})"
    else:
        text = f"waiting for approval #{result['approval_id']}"
    return f"{text}, replayed from idempotency key" if result.get("replayed") else text


def cmd_accounts(args: argparse.Namespace, ledger: Ledger) -> bool:
    for name, balance in ledger.accounts.items():
        print(f"{name:<10} {fmt(balance):>14}")
    return False


def cmd_transfer(args: argparse.Namespace, ledger: Ledger) -> bool:
    result = service.submit_transfer(
        ledger,
        args.src,
        args.dst,
        args.amount,
        actor="human",
        memo=args.memo,
        idempotency_key=args.key,
    )
    print(f"Transfer {fmt(args.amount)} {args.src} -> {args.dst}: {describe(result)}")
    return True


def cmd_run(args: argparse.Namespace, ledger: Ledger) -> bool:
    for call in agent.load_plan(args.plan):
        outcome = agent.run_call(ledger, call)
        print(f"[{call['id']}] {call['tool']}: {json.dumps(outcome)}")
    return True


def cmd_approvals(args: argparse.Namespace, ledger: Ledger) -> bool:
    pending = [a for a in ledger.approvals if a["status"] == "pending"]
    if not pending:
        print("Nothing waiting for approval.")
    for a in pending:
        print(f"#{a['id']:<3} {a['from']} -> {a['to']}  {fmt(a['amount'])}  by {a['requested_by']}  {a['memo']}")
    return False


def cmd_approve(args: argparse.Namespace, ledger: Ledger) -> bool:
    result = service.approve(ledger, args.id, args.by)
    print(f"Approval #{args.id}: {describe(result)}")
    return True


def cmd_audit(args: argparse.Namespace, ledger: Ledger) -> bool:
    if not ledger.audit:
        print("No transfers yet.")
    for e in ledger.audit:
        print(
            f"#{e['id']:<3} {e['at']}  {e['actor']:<10} {e['from']} -> {e['to']}  "
            f"{fmt(e['amount'])} (fee {fmt(e['fee'])})  {e['memo']}"
        )
    return False


def cmd_reconcile(args: argparse.Namespace, ledger: Ledger) -> bool:
    with open(args.statement, newline="") as f:
        rows = list(csv.DictReader(f))
    mismatches = 0
    for row in rows:
        expected = parse_amount(row["balance"])
        actual = ledger.balance(row["account"])
        status = "OK" if actual == expected else "MISMATCH"
        mismatches += status == "MISMATCH"
        print(f"{status:<9} {row['account']:<10} ledger {fmt(actual):>12}  statement {fmt(expected):>12}")
    if mismatches:
        raise ValueError(f"{mismatches} account(s) do not match the bank statement")
    return False


COMMANDS = {
    "accounts": cmd_accounts,
    "transfer": cmd_transfer,
    "run": cmd_run,
    "approvals": cmd_approvals,
    "approve": cmd_approve,
    "audit": cmd_audit,
    "reconcile": cmd_reconcile,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="payagent", description="Run a payments agent safely.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a ledger with demo accounts")
    init.add_argument("--force", action="store_true", help="overwrite an existing ledger")

    sub.add_parser("accounts", help="show balances")

    transfer = sub.add_parser("transfer", help="move money by hand")
    transfer.add_argument("src")
    transfer.add_argument("dst")
    transfer.add_argument("amount", type=parse_amount)
    transfer.add_argument("--memo", default="")
    transfer.add_argument("--key", help="idempotency key")

    run = sub.add_parser("run", help="execute an agent's tool calls from a .jsonl file")
    run.add_argument("plan")

    sub.add_parser("approvals", help="list transfers waiting for approval")

    approve = sub.add_parser("approve", help="approve a pending transfer")
    approve.add_argument("id", type=int)
    approve.add_argument("--by", default="ops-lead", help="who is approving")

    sub.add_parser("audit", help="show every executed transfer")

    reconcile = sub.add_parser("reconcile", help="compare balances to a bank statement CSV")
    reconcile.add_argument("statement")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = storage.get_path()
    try:
        if args.command == "init":
            if path.exists() and not args.force:
                raise LedgerError(f"{path} already exists (use --force to start over)")
            storage.save(path, storage.new_ledger())
            print(f"Created {path}")
            return 0
        ledger = storage.load(path)
        changed = COMMANDS[args.command](args, ledger)
    except (LedgerError, PolicyError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if changed:
        storage.save(path, ledger)
    return 0
