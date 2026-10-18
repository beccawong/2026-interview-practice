# expenses: a buggy CLI for debugging practice

A small expense tracker built with only the standard library (`argparse`, `json`, `csv`,
`dataclasses`). It has **several planted bugs**. Your job is to find and fix them.

## Setup

```sh
uv sync
uv run python-cli --help        # or: uv run python -m python_cli --help
```

Data is stored in `~/.expenses.json`. To keep practice data separate, point the CLI at a
scratch file:

```sh
export EXPENSES_FILE=/tmp/expenses-practice.json
```

## How to practice (interview-style)

1. Read `BUG_REPORTS.md`. These are complaints from users, not explanations of the bugs.
2. Reproduce each bug from the command line **before** reading the code.
3. Find the root cause, fix it, then confirm the repro no longer fails.
4. Narrate out loud as you go. Interviewers care about your process as much as the fix.
5. Check yourself with `uv run pytest`. The tests describe correct behavior, and all of them
   fail at the start.
6. Spoilers live in `SOLUTIONS.md`. Try not to open it until you're done.

Give yourself about 45 minutes. Reset with `git checkout -- src` to try again.

## Python debugging cheat sheet

- **Read tracebacks bottom-up.** The last line is the exception. The frame just above it is
  where it happened.
- `breakpoint()`: drop this anywhere to open `pdb`.
  - `n` next line, `s` step into, `c` continue, `r` run until return
  - `p expr` / `pp expr` print a value, `l` / `ll` show code, `w` show the stack,
    `u` / `d` move up/down the stack
- `uv run python -m pdb -m python_cli list` runs the whole CLI under the debugger.
- `uv run pytest -x --pdb` stops at the first failing test and opens the debugger there.
- `uv run pytest -k delete -v` runs only the tests whose names match.
- Quick inspection: `print(repr(x), type(x))`. `repr` shows the difference between `"12"` and
  `12`.
- `uv run python -i -c "from python_cli import report"` imports code into a REPL so you can
  poke at it.
