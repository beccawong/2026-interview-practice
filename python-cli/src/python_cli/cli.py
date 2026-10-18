import argparse
import csv
import sys

from python_cli import report, storage
from python_cli.models import Expense, make_expense


def fmt(e: Expense) -> str:
    tags = f" [{', '.join(e.tags)}]" if e.tags else ""
    return f"{e.date}  {e.category:<12} ${e.amount:>8.2f}  {e.note}{tags}"


def cmd_add(args: argparse.Namespace, expenses: list[Expense]) -> bool:
    kwargs = {"tags": args.tag} if args.tag else {}
    expense = make_expense(args.amount, args.category, args.date, args.note, **kwargs)
    expenses.append(expense)
    print(f"Added: {fmt(expense)}")
    return True


def cmd_list(args: argparse.Namespace, expenses: list[Expense]) -> bool:
    shown = report.filter_expenses(expenses, args.month, args.category)
    if not shown:
        print("No expenses found.")
    for i, e in enumerate(shown, start=1):
        print(f"{i:>3}. {fmt(e)}")
    return False


def cmd_delete(args: argparse.Namespace, expenses: list[Expense]) -> bool:
    removed = expenses.pop(args.id - 1)
    print(f"Deleted: {fmt(removed)}")
    return True


def cmd_clear(args: argparse.Namespace, expenses: list[Expense]) -> bool:
    count = report.remove_category(expenses, args.category)
    print(f"Removed {count} expense(s) in '{args.category}'.")
    return count > 0


def cmd_summary(args: argparse.Namespace, expenses: list[Expense]) -> bool:
    rows = report.summarize(report.filter_expenses(expenses, args.month))
    if not rows:
        print("No expenses found.")
    for category, total, percent in rows:
        print(f"{category:<12} ${total:>8.2f}  {percent:>5.1f}%")
    return False


def cmd_import(args: argparse.Namespace, expenses: list[Expense]) -> bool:
    with open(args.csv_file, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        expenses.append(
            make_expense(float(row["amount"]), row["category"], row.get("date"), row.get("note", ""))
        )
    print(f"Imported {len(rows)} expense(s).")
    return True


COMMANDS = {
    "add": cmd_add,
    "list": cmd_list,
    "delete": cmd_delete,
    "clear": cmd_clear,
    "summary": cmd_summary,
    "import": cmd_import,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="expenses", description="Track your spending.")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="add an expense")
    add.add_argument("amount")
    add.add_argument("category")
    add.add_argument("--date", help="YYYY-MM-DD (default: today)")
    add.add_argument("--note", default="")
    add.add_argument("--tag", action="append", help="may be repeated")

    ls = sub.add_parser("list", help="list expenses")
    ls.add_argument("--month", help="YYYY-MM")
    ls.add_argument("--category")

    delete = sub.add_parser("delete", help="delete an expense by its number in `list`")
    delete.add_argument("id", type=int)

    clear = sub.add_parser("clear", help="delete every expense in a category")
    clear.add_argument("--category", required=True)

    summary = sub.add_parser("summary", help="totals per category")
    summary.add_argument("--month", help="YYYY-MM")

    imp = sub.add_parser("import", help="import expenses from a CSV file")
    imp.add_argument("csv_file")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = storage.get_path()
    expenses = storage.load(path)
    try:
        changed = COMMANDS[args.command](args, expenses)
    except (ValueError, IndexError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if changed:
        storage.save(path, expenses)
    return 0
