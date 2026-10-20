import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PLANS = ROOT / "plans"


@pytest.fixture
def run(tmp_path, monkeypatch):
    db = tmp_path / "ledger.json"
    monkeypatch.setenv("PAYAGENT_FILE", str(db))

    def _run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "payagent", *args],
            capture_output=True,
            text=True,
        )

    def balances() -> dict[str, Decimal]:
        data = json.loads(db.read_text())
        return {name: Decimal(v) for name, v in data["accounts"].items()}

    _run.balances = balances
    assert _run("init").returncode == 0
    return _run


def test_unknown_tool_is_reported_to_the_agent(run):
    result = run("run", str(PLANS / "vendor_lookup.jsonl"))
    assert result.returncode == 0, result.stderr
    assert "unknown tool" in result.stdout
    assert run.balances()["acme"] == Decimal("10.00")


def test_agent_amounts_are_exact(run):
    run("run", str(PLANS / "invoices.jsonl"))
    result = run("reconcile", str(ROOT / "statements" / "invoices.csv"))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "MISMATCH" not in result.stdout


def test_failed_transfer_does_not_move_money(run):
    result = run("run", str(PLANS / "typo.jsonl"))
    assert "unknown account 'acme-corp'" in result.stdout
    assert run.balances()["ops"] == Decimal("5000.00")


def test_agent_retry_with_same_idempotency_key_pays_once(run):
    result = run("run", str(PLANS / "retry.jsonl"))
    assert "replayed" in result.stdout
    assert run.balances()["acme"] == Decimal("250.00")


def test_daily_limit_is_enforced(run):
    result = run("run", str(PLANS / "payday.jsonl"))
    lines = result.stdout.strip().splitlines()
    assert "daily limit" in lines[2]
    assert run.balances()["acme"] + run.balances()["globex"] == Decimal("800.00")


def test_negative_amounts_are_blocked(run):
    result = run("run", str(PLANS / "credit_note.jsonl"))
    assert '"ok": false' in result.stdout
    assert run.balances()["ops"] == Decimal("5000.00")
    assert run.balances()["acme"] == Decimal("0.00")

    result = run("transfer", "ops", "acme", "-5")
    assert result.returncode != 0
    assert "error" in result.stderr


def test_fee_rounds_half_up(run):
    run("transfer", "ops", "globex", "36.50")
    assert run.balances()["fees"] == Decimal("0.37")


def test_approving_twice_pays_once(run):
    run("transfer", "ops", "acme", "600")
    assert run("approve", "1").returncode == 0
    assert "Nothing waiting" in run("approvals").stdout
    second = run("approve", "1")
    assert second.returncode != 0
    assert "already approved" in second.stderr
    assert run.balances()["acme"] == Decimal("600.00")
