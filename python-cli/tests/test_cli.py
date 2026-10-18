import json
import subprocess
import sys
from pathlib import Path

import pytest

SAMPLE_CSV = Path(__file__).parent.parent / "sample.csv"


@pytest.fixture
def run(tmp_path, monkeypatch):
    db = tmp_path / "expenses.json"
    monkeypatch.setenv("EXPENSES_FILE", str(db))

    def _run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "python_cli", *args],
            capture_output=True,
            text=True,
        )

    _run.db = db
    return _run


def test_add_twice_keeps_both(run):
    assert run("add", "5", "coffee").returncode == 0
    assert run("add", "10", "lunch").returncode == 0
    data = json.loads(run.db.read_text())
    assert len(data) == 2


def test_amount_is_stored_as_number(run):
    run("add", "12.50", "lunch")
    data = json.loads(run.db.read_text())
    assert data[0]["amount"] == 12.5


def test_date_is_parsed_as_year_month_day(run):
    run("add", "5", "coffee", "--date", "2026-03-05")
    data = json.loads(run.db.read_text())
    assert data[0]["date"] == "2026-03-05"


def test_delete_uses_number_shown_in_list(run):
    run("add", "1", "a")
    run("add", "2", "b")
    run("add", "3", "c")
    run("delete", "1")
    remaining = [e["category"] for e in json.loads(run.db.read_text())]
    assert remaining == ["b", "c"]


def test_delete_out_of_range_exits_nonzero(run):
    run("add", "1", "a")
    result = run("delete", "5")
    assert result.returncode != 0
    assert "error" in result.stderr


def test_clear_removes_every_match(run):
    for _ in range(3):
        run("add", "1", "coffee")
    run("add", "1", "lunch")
    result = run("clear", "--category", "coffee")
    assert "Removed 3" in result.stdout
    remaining = [e["category"] for e in json.loads(run.db.read_text())]
    assert remaining == ["lunch"]


def test_import_tags_are_per_expense(run):
    run("import", str(SAMPLE_CSV))
    data = json.loads(run.db.read_text())
    tags = {e["note"]: e["tags"] for e in data}
    assert tags["latte"] == ["treat"]
    assert tags["weekly shop"] == ["essential"]
    assert tags["sandwich"] == []


def test_summary_biggest_first_with_percent(run):
    run("add", "75", "rent")
    run("add", "25", "coffee")
    lines = run("summary").stdout.strip().splitlines()
    assert lines[0].startswith("rent")
    assert "75.0%" in lines[0]
    assert lines[1].startswith("coffee")
    assert "25.0%" in lines[1]
