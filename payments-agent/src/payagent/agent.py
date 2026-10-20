"""Executes tool calls emitted by the payments agent.

The model never touches the ledger directly. The agent runtime writes one JSON tool call per
line (see plans/), and this module runs each one through the same guardrails a human goes
through. The returned dict is what gets sent back to the model as the tool result.
"""

import json
from pathlib import Path

from payagent import service
from payagent.ledger import Ledger, LedgerError
from payagent.money import parse_amount
from payagent.policy import PolicyError

AGENT_ACTOR = "agent"


def tool_get_balance(ledger: Ledger, call: dict) -> dict:
    account = call["args"]["account"]
    return {"account": account, "balance": str(ledger.balance(account))}


def tool_transfer(ledger: Ledger, call: dict) -> dict:
    args = call["args"]
    return service.submit_transfer(
        ledger,
        args["from"],
        args["to"],
        parse_amount(args["amount"]),
        actor=AGENT_ACTOR,
        memo=args.get("memo", ""),
        idempotency_key=call["id"],
    )


TOOLS = {
    "get_balance": tool_get_balance,
    "transfer": tool_transfer,
}


def run_call(ledger: Ledger, call: dict) -> dict:
    """Run one tool call and return the result for the model."""
    tool = TOOLS.get(call["tool"])
    try:
        return {"ok": True, "result": tool(ledger, call)}
    except (LedgerError, PolicyError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


def load_plan(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
