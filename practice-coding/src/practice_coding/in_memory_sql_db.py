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
import unittest
from dataclasses import dataclass
from typing import Any


@dataclass
class DbTable:
    name: str
    metadata: dict
    data: list

class InMemoryDb:
    def __init__(self):
        # tablename: {data: [{colName: value...}], metadata: {}}
        self.table_data: dict[str, DbTable] = {}

    def create_table(self, name: str, columns: list[str]):
        if name in self.table_data:
            raise ValueError

        table = DbTable(name, {"columns": set(columns)}, [])
        self.table_data[name] = table
        return True

    def insert(self, table_name: str, row: dict[str, Any]):
        row_to_insert = {}
        table = self.table_data[table_name]
        for k, v in row:
            if k not in table.metadata["cols"]:
                raise ValueError
            if k in row_to_insert:
                raise ValueError
            row_to_insert[k] = v
        table.data.append(row_to_insert)

    def _compare(self, op: str, left: Any, right: Any) -> bool:
        match op:
            case "==":
                return left == right
            case "<=":
                return left <= right
            case ">=":
                return left >= right
            case "!=":
                return left != right
            case "<":
                return left < right
            case ">":
                return left > right
            case _:
                raise ValueError("Unknown operation")
    

    def select(self, table_name: str, where: list[tuple[str, str, Any]]) -> list[dict]:
        data_rows = self.table_data[table_name].data
        result = []

        for row in data_rows:
            accept = True
            for condition in where:
                pred_col = condition[0]
                pred_op = condition[1]
                pred_val = condition[2]
                accept = accept and self._compare(pred_op, row[pred_col], pred_val)
                if not accept:
                    break
            if accept:
                result.append(row)

        return result

    def sort_rows(self, table_name: str, order_by: list[tuple[str, str]]) -> list[dict]:
        data_rows = self.table_data[table_name].data
        for clause in order_by:


class TestInMemoryDb(unittest.TestCase):
    TABLE_NAME_1 = "test_table"
    def setUp(self):
        self.db = InMemoryDb()
        self.db.create_table("test_table", ["col1", "col2"])

    def test_insert_into_new_table(self):
        self.db.insert(self.TABLE_NAME_1, {"col1": 1, "col2": 34})

    def test_insert_with_missing_cols(self):
        pass

    def test_insert_with_all_cols_missing(self):
        pass

    def test_insert_with_invalid_cols(self):
        pass

    def test_insert_with_invalid_table(self):
        pass

    def test_insert_with_more_cols(self):
        pass

    def solve(slot_index):
        