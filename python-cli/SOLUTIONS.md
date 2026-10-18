# Solutions (spoilers!)

| # | File | Root cause | Fix |
|---|------|-----------|-----|
| 1 | `storage.py` `save` | The file is opened with `"a"` (append), so the second save writes a second JSON array after the first one and the file is no longer valid JSON. | `open(path, "w")` |
| 2 | `cli.py` `add` parser **and** `cmd_import` | Command-line arguments and CSV fields are always strings. `amount` is never converted, so `:.2f` formatting fails and `sum` adds a str to an int. | `add.add_argument("amount", type=float)` and `float(row["amount"])`. You have to fix both places. Easy to miss the second! |
| 3 | `models.py` `DATE_FORMAT` | `"%Y-%d-%m"` swaps day and month. `2026-03-05` is stored as May 3rd. `2026-03-10` would mean month 10 and survives, while a day above 12 raises `ValueError`. | `"%Y-%m-%d"` |
| 4 | `cli.py` `cmd_delete` | `list` numbers items from 1, but `pop()` takes a 0-based index. Also, `delete 0` and `delete -1` silently delete items. | Check `1 <= args.id <= len(expenses)` (raise `IndexError` otherwise), then `expenses.pop(args.id - 1)`. |
| 5 | `report.py` `remove_category` | Removing items from a list while iterating over it skips the element after each removal. | Rebuild the list: `kept = [e for e in expenses if e.category != cat]`, `removed = len(expenses) - len(kept)`, `expenses[:] = kept`. Or iterate over a copy: `for e in list(expenses):`. |
| 6 | `models.py` `make_expense` | Mutable default argument. `tags=[]` is created **once** when the function is defined, so every call shares the same list and every expense points at it. | `tags=None`, then `tags = list(tags) if tags else []` inside the function. |
| 7 | `report.py` `summarize` | (a) `sorted` without `reverse=True` puts the smallest first. (b) `//` is floor division, so `25 // 100 == 0` and `100 // 100 == 1`. | `sorted(..., key=lambda kv: kv[1], reverse=True)` and `amount / grand * 100`. |
| 8 | `__init__.py` `main` (and `__main__.py`) | `cli.main()` returns 1 on error, but that return value is thrown away, so the process exits with 0. | `sys.exit(cli.main())` |

## Bonus discussion points (often asked as follow-ups)
- Floats for money: `0.1 + 0.2 != 0.3`. Use `decimal.Decimal` or integer cents.
- `save` is not atomic. A crash mid-write corrupts the file. Write to a temp file, then `os.replace`.
- `load` doesn't handle a corrupt file gracefully. You could catch `json.JSONDecodeError` and
  show a friendly message.
- `except (ValueError, IndexError, OSError)` in `main` hides tracebacks. Is a `--debug` flag
  worth adding?
- How would you have caught these earlier? With type hints + `mypy`, `make_expense` has no
  annotations, which is how the string amount slipped through. Unit tests on `report.py`
  would catch 5 and 7.
