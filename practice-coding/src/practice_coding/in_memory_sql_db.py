"""
In-Memory SQL-like Database

Reported scope is deliberately small: no primary indexes, no typed or
generic column definitions, no joins across tables.

Part 1 - Tables and inserts
    create_table(name, columns: list[str])
    insert(table_name, row: dict[str, Any])
    Reject rows with unknown columns. Decide what to do with missing columns.

Part 2 - select with where
    select(table_name, where=None) -> list[dict]
    `where` is a list of (column, op, value) conditions combined with AND
    only. Support at least ==, !=, <, <=, >, >=.

Part 3 - order_by
    select(table_name, where=None, order_by=None)
    order_by is a list of (column, "asc" | "desc"), applied in priority
    order (multi-key sort with mixed directions).

Part 4 - Follow-ups to be ready to discuss
    - Projection: select only some columns.
    - update / delete with a where clause.
    - Adding an index on a column to speed up == lookups. How do you keep
      it in sync on insert/update/delete?
    - Combine with tx_database.py: begin / commit / rollback.

Sources:
    https://www.coditioning.com/blog/14/open-ai-swe-coding-interviewquestions-actual-questions-real-candidates
    https://www.linkjob.ai/interview-questions/openai-coding-interview/
    https://sx-studio.com/openai-sde-interview/
"""
