"""
Spreadsheet with Formula Dependencies

Builds on topological_sort.py and depth_first_search.py.

Part 1 - Values only
    set_cell(cell_id: str, value: int)
    get_cell(cell_id: str) -> int
    Unset cells read as 0.

Part 2 - Formulas (lazy evaluation)
    set_cell(cell_id, formula) where the formula is a sum of cell references
    and/or ints, e.g. "=A1+B2+5". get_cell computes the value on demand by
    recursively evaluating references.

Part 3 - Cycle detection
    set_cell("A1", "=B1"); set_cell("B1", "=A1") must raise, and must leave
    the sheet unchanged (the rejected set has no effect).

Part 4 - O(1) get_cell (the reported follow-up)
    Cache every cell's computed value. When a cell changes, push the change
    to everything that depends on it, recomputing in topological order so
    each dependent is recomputed exactly once.
    You'll need both directions of the graph: what a cell depends on, and
    which cells depend on it. Remember to remove old dependency edges
    when a formula is replaced.

Part 5 - Follow-ups to be ready to discuss
    - Complexity of set_cell vs get_cell in each approach; which suits
      read-heavy vs write-heavy workloads.
    - Supporting ranges like SUM(A1:A10).

Sources:
    https://www.coditioning.com/blog/14/open-ai-swe-coding-interviewquestions-actual-questions-real-candidates
    https://www.1point3acres.com/interview/thread/1149658
"""
