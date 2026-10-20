# Solutions (spoilers!)

| # | File | Root cause | Fix |
|---|------|-----------|-----|
| 1 | `agent.py` `run_call` | `TOOLS.get(...)` returns `None` for an unknown tool, and calling `None(...)` raises `TypeError`. That isn't in the `except` tuple, so it escapes, the CLI crashes, and nothing is saved. | `if tool is None: return {"ok": False, "error": f"unknown tool '{call['tool']}'"}` before the `try`. Don't "fix" it by catching `Exception`, because that hides real bugs. |
| 2 | `money.py` `parse_amount` | `json.loads` turns `19.99` into a **float**, and `Decimal(19.99)` captures the float's binary error: `Decimal('19.98999999999999843680598132...')`. `fmt()` rounds to 2 places, so the output looks right while `==` fails. `cat $PAYAGENT_FILE` shows the long numbers. | `Decimal(str(value))` for floats. Even better, reject floats at the boundary, or load plans with `json.loads(line, parse_float=Decimal)`. Note that `120.00` happens to be exact in binary, which is why `globex` reconciles. |
| 3 | `ledger.py` `move` | `src` is debited *before* `self.balance(dst)` validates the destination. The `LedgerError` is caught in `run_call` and reported to the agent, the run continues, and the half-applied transfer is saved. | Validate everything first, then mutate: look up `self.balance(dst)` (and the fees account) before any `-=`. Debit/credit should be all-or-nothing. |
| 4 | `agent.py` `tool_transfer` | Deduplication uses `call["id"]`, the tool-call id, which is new on every retry. The real idempotency key is `args["idempotency_key"]`. | `idempotency_key=args.get("idempotency_key")`. Arguably it should be **required** for the agent. |
| 5 | `policy.py` `spent_today` | `e["at"]` is a full timestamp (`2026-10-19T14:03:22+00:00`) compared with `==` to a date (`2026-10-19`). It never matches, so `spent` is always 0. | `e["at"].startswith(day)`, or better, `datetime.fromisoformat(e["at"]).date() == today`. |
| 6 | `policy.py` `check` | Nothing rejects zero or negative amounts. A negative transfer runs in reverse, and the fee goes negative too. This is a prompt-injection path: text in an invoice controls the model, so the executor must validate. | `if amount <= 0: raise PolicyError("amount must be positive")`. Also reject more than 2 decimal places (`amount != amount.quantize(CENT)`). |
| 7 | `money.py` `fee_for` | `Decimal.quantize` uses the context rounding mode, which defaults to `ROUND_HALF_EVEN` (banker's rounding). `0.365` becomes `0.36`. The docstring says the processor rounds half up. | `.quantize(CENT, rounding=ROUND_HALF_UP)` |
| 8 | `service.py` `approve` | `approval["status"] == "approved"` is a comparison, not an assignment. Its result is thrown away, so the status stays `pending`. | `approval["status"] = "approved"`. A linter flags this (ruff `B015`, "pointless comparison"). |

## Bonus discussion points (common follow-ups)

- **Four-eyes principle.** `approve` doesn't stop the requester from approving their own
  transfer, and `--by` is self-reported. How would you authenticate the approver?
- **Daily limit vs. approvals.** Pending approvals don't count toward the daily limit, and
  `approve` skips `policy.check` entirely. Is approval a policy override, or should the limit
  be re-checked at execution time?
- **Idempotency edge cases.** What if the same key comes back with a *different* amount? (Real
  APIs like Stripe return an error.) Should failed attempts be cached? Here they aren't, so a
  retry after "insufficient funds" can succeed later. Is that what you want?
- **Concurrency.** Two `payagent` processes can load, both pass the daily-limit check, and both
  save, so the last writer wins and one transfer disappears from the books. You need a file lock,
  or a real database with transactions and `SELECT ... FOR UPDATE`.
- **Untrusted model output.** `args["amount"]` and friends raise `KeyError` (uncaught, so a
  crash) when the model omits a field. Validate tool arguments against a schema (pydantic, JSON
  Schema) and send validation errors back to the model so it can correct itself.
- **What the model sees.** Error strings go straight back to the LLM. Is it OK for the model to
  learn exact balances from "insufficient funds" messages? What should be redacted?
- **Audit completeness.** Only executed transfers are logged. Compliance usually wants blocked
  and failed attempts too, with the reason.
- **Prevention.** Which of these would type hints + `mypy` catch? (#1: `tool` is
  `Callable | None`.) Which would a linter catch? (#8.) Property-based tests with `hypothesis`
  ("money is conserved: sum of all balances never changes") would catch #3 and #6 instantly.
