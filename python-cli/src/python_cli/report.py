from python_cli.models import Expense


def filter_expenses(
    expenses: list[Expense], month: str | None = None, category: str | None = None
) -> list[Expense]:
    result = expenses
    if month:
        result = [e for e in result if e.date.startswith(month)]
    if category:
        result = [e for e in result if e.category == category.lower()]
    return result


def remove_category(expenses: list[Expense], category: str) -> int:
    """Remove every expense in `category` from the list in place. Returns the count removed."""
    removed = 0
    for e in expenses:
        if e.category == category.lower():
            expenses.remove(e)
            removed += 1
    return removed


def totals_by_category(expenses: list[Expense]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for e in expenses:
        totals[e.category] = totals.get(e.category, 0) + e.amount
    return totals


def summarize(expenses: list[Expense]) -> list[tuple[str, float, float]]:
    """Return (category, total, percent_of_grand_total) rows, biggest category first."""
    totals = totals_by_category(expenses)
    grand = sum(totals.values())
    rows = []
    for category, amount in sorted(totals.items(), key=lambda kv: kv[1]):
        rows.append((category, amount, amount // grand * 100))
    return rows
