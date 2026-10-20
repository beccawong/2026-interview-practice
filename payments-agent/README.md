# payagent: a buggy payments-agent executor for debugging practice

An LLM agent pays vendor invoices. The model never touches money directly. Instead, the agent
runtime writes the agent's **tool calls** to a `.jsonl` file (one JSON object per line, see
`plans/`), and `payagent run` executes them against a ledger. Each call goes through the same
guardrails a human transfer goes through. Those guardrails are:

- **Idempotency keys**: an invoice must never be paid twice, even when the agent retries.
- **Daily limit**: at most $1,000.00 can leave an account per (UTC) day.
- **Approval threshold**: transfers over $500.00 wait in a queue until a human runs `approve`.
- **Fees**: 1% of every transfer, rounded to the cent, goes to the `fees` account.

Standard library only (`argparse`, `decimal`, `json`, `csv`, `dataclasses`). There are
**several planted bugs**. Your job is to find and fix them.

## Setup

```sh
uv sync
export PAYAGENT_FILE=/tmp/payagent-practice.json   # keep practice data out of ~/.payagent.json
uv run payagent init --force                        # ops: $5,000, acme/globex/fees: $0
uv run payagent --help
```

Commands: `init`, `accounts`, `transfer SRC DST AMOUNT [--key K]`, `run PLAN.jsonl`,
`approvals`, `approve ID`, `audit`, `reconcile STATEMENT.csv`.

## Layout

| File | What it does |
|------|--------------|
| `cli.py` | argparse wiring, printing, exit codes |
| `agent.py` | tool registry, runs one tool call and builds the result for the model |
| `service.py` | `submit_transfer` (the single entry point for moving money) and `approve` |
| `policy.py` | guardrails: daily limit, approval threshold |
| `ledger.py` | balances and the actual debit/credit |
| `money.py` | parsing amounts, fees, formatting |
| `storage.py` | JSON persistence |

## How to practice (interview-style)

1. Read `BUG_REPORTS.md`. These are complaints from the ops team, not explanations of the bugs.
2. Reproduce each one from the command line **before** reading the code. Run
   `payagent init --force` between repros so earlier runs don't muddy the numbers.
3. Find the root cause, fix it, then confirm the repro no longer fails.
4. Narrate out loud. For a FinTech interviewer, say *why* a bug matters (money lost, compliance,
   trust), not only what's wrong.
5. Check yourself with `uv run pytest`. The tests describe correct behavior. All of them fail at
   the start.
6. Spoilers live in `SOLUTIONS.md`. Try not to open it until you're done.

Give yourself about 45–60 minutes. Reset with `git checkout -- src` to try again.

## Debugging tips for this one

- `cat $PAYAGENT_FILE` is your friend. The stored JSON sometimes shows what the pretty
  `$1,234.56` output hides.
- `Decimal` prints its exact value with `repr()`: `print(repr(x))`.
- `uv run python -m pdb -m payagent run plans/retry.jsonl` runs a plan under the debugger.
- `uv run pytest -x --pdb` stops at the first failing test and opens the debugger there.
- `uv run pytest -k idempotency -v` runs only the tests whose names match.
- REPL poking: `uv run python -i -c "from payagent.money import *"`.
