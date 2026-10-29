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

import asyncio


async def main():
    pass

asyncio.run(main())