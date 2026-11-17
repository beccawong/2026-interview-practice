"""
Resumable Iterator

Most consistently reported OpenAI coding question. Reportedly run tests-first:
you write the test cases before the implementation.

Part 1 - Tests first
    Before writing any implementation, write tests for an iterator over a list
    that supports:
        - __iter__ / __next__ (raises StopIteration at the end)
        - get_state() -> an opaque state value
        - set_state(state) -> resumes from exactly that position
    Think about: empty list, saving at the start / middle / end, restoring
    an old state after iterating further, restoring the same state twice.

Part 2 - ListIterator
    Implement the iterator so your Part 1 tests pass.
    The state must be small (e.g. an index), never a copy of the data.

Part 3 - Abstract interface
    Extract a ResumableIterator abstract base class so the same tests
    can run against any implementation.

Part 4 - FileIterator
    Iterate over lines (or JSON records) in a single file. The state should
    be something like a byte offset so restore doesn't re-read the file
    from the beginning.

Part 5 - MultiFileIterator
    Iterate over several files in sequence as one stream. The state must
    capture which file you're in plus the position within it. Handle
    empty files in the middle of the list.

Part 6 - Follow-ups to be ready to discuss
    - The state must survive a process restart (make it serializable).
    - Async version (async iterator over a slow source).
    - What happens if the underlying file changes between save and restore?

Sources:
    https://prachub.com/coding-questions/design-a-resumable-iterator-with-checkpoint-and-restore
    https://www.hellointerview.com/community/questions/resumable-iterator/cmbskz7ck004r07ad6f1jxlni
    https://www.coditioning.com/blog/14/open-ai-swe-coding-interviewquestions-actual-questions-real-candidates
    https://igotanoffer.com/en/advice/openai-coding-interview
"""

import tempfile
import unittest
from abc import abstractmethod
from collections.abc import Iterator
from typing import TYPE_CHECKING


class ResumableIterator(Iterator):
    @abstractmethod
    def save_state(self):
        pass

    @abstractmethod
    def resume(self, state):
        pass

class ListResumbleIterator[T](ResumableIterator):
    def __init__(self, data: list[T]):
        self.data = data
        self.cursor = 0

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> T:
        if self.cursor >= len(self.data):
            raise StopIteration
        result = self.data[self.cursor]
        self.cursor += 1
        return result

    def save_state(self) -> dict:
        return {"cursor": self.cursor}

    def resume(self, state: dict):
        self.cursor = state.get("cursor", -1)
        if self.cursor == -1:
            raise ValueError

class FileResumbleIterator(ResumableIterator):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.cursor = 0
        self.file = open(file_path, "r")

    def __iter__(self) -> Iterator:
            return self
    
    def __next__(self) -> str:
        result = self.file.readline()
        self.cursor = self.file.tell()
        if not result:
            self.file.close()
            raise StopIteration
        return result.strip()

    def save_state(self):
        return {"cursor": self.cursor}

    def resume(self, state):
        position = state.get("cursor", None)
        if None:
            raise ValueError
        self.file.seek(position)

class MultiFileResumableIterator(ResumableIterator):
    def __init__(self, file_paths: list[str]):
        self.files = file_paths
        self.current_file_index = 0
        self.cursor = 0
        self.file = open(file_paths[self.current_file_index], "r")

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> str:
        result = self.file.readline()
        if result:
            self.cursor = self.file.tell()
            return result.strip()
        else:
            self.file.close()
            while self.current_file_index < len(self.files) - 1:
                self.current_file_index += 1
                self.file = open(self.files[self.current_file_index], "r")
                result = self.file.readline()
                if result:
                    self.cursor = self.file.tell()
                    return result.strip()
            self.file.close()
            raise StopIteration

    def save_state(self):
        return {"cursor": self.cursor, "file_index": self.current_file_index}

    def resume(self, state):
        cursor = state.get("cursor", None)
        file_index = state.get("file_index", None)
        if cursor is None or file_index is None:
            raise ValueError
        self.file = open(self.files[file_index], "r")
        self.cursor = cursor
        self.current_file_index = file_index


# Type checkers see a TestCase base (so self.assertEqual etc. resolve);
# at runtime it's a plain object, so unittest doesn't collect the mixin.
if TYPE_CHECKING:
    _TestCaseBase = unittest.TestCase
else:
    _TestCaseBase = object


class BaseListResumableIteratorTests(_TestCaseBase):
    def get_empty_iterator(self) -> ResumableIterator:
        raise NotImplementedError

    def get_iterator_with_data(self, count: int) -> ResumableIterator:
        raise NotImplementedError
    
    def test_next_gets_next_item(self):
        iterator = self.get_iterator_with_data(2)
        self.assertEqual(iterator.__next__(), "line0")
        self.assertEqual(iterator.__next__(), "line1")

    def test_next_raises_when_no_item_left(self):
        iterator = self.get_iterator_with_data(1)
        iterator.__next__()
        with self.assertRaises(StopIteration):
            iterator.__next__()

    def test_save_state_save_cursor(self):
        iterator = self.get_iterator_with_data(1)
        state = iterator.save_state()
        self.assertEqual(state, {"cursor": 0})

    def test_resume_from_save_state(self):
        iterator = self.get_iterator_with_data(2)
        iterator.__next__()
        state = iterator.save_state()
        iterator.resume(state)
        self.assertEqual(iterator.__next__(), "line1")

    def test_save_state_empty_list(self):
        iterator = self.get_empty_iterator()
        state = iterator.save_state()
        iterator.resume(state)

class TestListResumableIterator(BaseListResumableIteratorTests, unittest.TestCase):
    def get_empty_iterator(self) -> ResumableIterator:
        return ListResumbleIterator([])

    def get_iterator_with_data(self, count: int) -> ResumableIterator:
        data = [f"line{i}" for i in range(count)]
        return ListResumbleIterator(data)

class TestFileResumableIterator(BaseListResumableIteratorTests, unittest.TestCase):
    def setUp(self):
        self.test_file = tempfile.NamedTemporaryFile(mode="w", delete_on_close=True)

    def tearDown(self) -> None:
        self.test_file.close()

    def get_empty_iterator(self) -> ResumableIterator:
        return FileResumbleIterator(self.test_file.name)

    def get_iterator_with_data(self, count: int) -> ResumableIterator:
        data = [f"line{i}\n" for i in range(count)]
        print(data)
        self.test_file.writelines(data)
        self.test_file.flush()
        return FileResumbleIterator(self.test_file.name)

if __name__ == "__main__":
    unittest.main()
                

