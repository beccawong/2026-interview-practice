1. Read up on aysncio python; create_task, gather, sleep
2. Read up on random library; choices

Claude's suggestion:
▗ ▗   ▖ ▖  Claude Code v2.1.312
           Opus 5.5 · Claude Pro
 ▘▘   ▝▝   ~/Development/2026-interview-practice/practice-coding


❯ I am getting stuck on questions in this directory because my Python is rusty. 
  For example, I didn't remember how to write unit tests, especially in         
  interview setting where everything is in one file. I didn't know the file     
  library to get byte offset and seek to it. I didn't remember how to start     
  asyncio loop. Based on the questions here, don't tell me the solutions, but   
  what would be good Python libraries and materials to brush up on. It's been a 
  while since I've written lines of code myself                                 

  Ran 1 shell command (ctrl+o to expand)

⏺ I read the problem statements in src/practice_coding/ and grouped the standard
  library by what the problems need. This covers which tools to learn, not how
  to solve anything.

  1. Testing in a single file (needed for every problem, and resumable iterator 
  is tests-first)

  - unittest: TestCase, setUp, assertEqual, assertRaises (as a context manager),
    subTest, and running it all with unittest.main() under if __name__ == 
    "__main__":. This runs anywhere, CoderPad included, with nothing to install.
  - unittest.mock: Mock, side_effect (return a sequence of values or raise
    exceptions), call_count, assert_called_with. You'll want these for the
    injected send(), fetch_links() and clock in the webhook, crawler and rate
    limiter problems.
  - pytest (if the interviewer allows it): plain assert, pytest.raises,
    @pytest.mark.parametrize, the tmp_path fixture, and running one file with
    python -m pytest file.py.
  - unittest.IsolatedAsyncioTestCase: for testing async code.
  - tempfile: NamedTemporaryFile and TemporaryDirectory, for making real files
    in FileIterator and persistence tests.

  2. Files and serialization (FileIterator, KV store persistence, limited-memory
  sort)

  - The built-in open() and the io module: text vs binary modes ("r" vs "rb"),
    readline(), tell(), seek(), flush(). Read the io docs on text vs binary
    streams. One gotcha to learn: what tell() returns in text mode, and why it
    doesn't mix with for line in f.
  - os.fsync: what it guarantees for an append-only log compared with flush().
  - json: dumps/loads, and the JSON Lines convention of one record per line.
  - pathlib.Path: the modern way to work with paths.
  - heapq.merge: worth knowing for sort_with_limited_memory.py.

  3. Iterator protocol and interfaces (resumable iterator)

  - __iter__/__next__, StopIteration, and generators (yield), plus what
    "iterable" means vs "iterator".
  - abc: ABC and @abstractmethod.
  - The async counterparts: __aiter__/__anext__, StopAsyncIteration, and async
    generators.

  4. Concurrency (rate limiter, KV store, crawler, webhook, worker pool)

  - asyncio: asyncio.run(), async def/await, create_task, gather, TaskGroup
    (3.11+), asyncio.Queue (also its task_done/join), Semaphore, Lock,
    wait_for/timeout, asyncio.sleep, to_thread.
  - threading: Thread, Lock vs RLock, Condition, Event.
  - concurrent.futures: ThreadPoolExecutor, submit, as_completed, map.
  - queue.Queue: the thread-safe queue, with the same task_done/join idea as
    asyncio's.
  - Be able to explain the GIL, and when to pick threads vs asyncio vs
    processes.

  5. Data structures (in nearly every problem)

  - collections: deque (sliding window, BFS), defaultdict, Counter (KNN voting),
    OrderedDict (TTL/LRU cache).
  - heapq: heappush/heappop, ordering with tuples, nsmallest. Used in credit
    expiry, KNN and retry scheduling.
  - bisect: bisect_left/bisect_right, insort, and the key= parameter (3.10+).
    Used in the versioned KV store.
  - dataclasses: field(default_factory=...), order=True, frozen=True.
  - enum: for states like those in minesweeper.

  6. Smaller utilities

  - Sorting: the docs' "Sorting HOWTO", especially sort stability and multi-key
    sorts, operator.itemgetter, and functools.cmp_to_key (in_memory_sql_db
    order_by).
  - functools: cache/lru_cache, partial.
  - time: time.monotonic() vs time.time(), and why to inject a clock.
  - random: uniform (backoff jitter), seed, choices.
  - math: math.dist, math.inf (KNN).
  - re: for parsing spreadsheet formulas like =A1+B2+5.
  - urllib.parse: urlparse, urljoin, urldefrag (crawler).
  - hmac, hashlib, uuid: webhook follow-ups (signing, idempotency keys).
  - numpy basics (broadcasting, argsort, argpartition): only for the KNN
    follow-up.

  Materials

  - Python Module of the Week (pymotw.com): short, runnable examples per stdlib
    module. It's the fastest way to relearn heapq, bisect, io, asyncio,
    threading and unittest.
  - Official docs: the "Sorting HOWTO", "Functional Programming HOWTO"
    (iterators and generators), and the asyncio pages "Coroutines and Tasks" and
    "Queues". The unittest page's "Basic example" covers single-file tests.
  - Fluent Python, 2nd ed. (Ramalho), most relevant chapters:
    - Ch. 5: data classes
    - Ch. 17: iterators and generators
    - Ch. 19–21: concurrency, futures, asyncio
  - Real Python: its "Async IO in Python" walkthrough and its unittest and
    pytest guides are beginner-friendly.
  - Effective Python (Slatkin): short items on idioms and concurrency, good for
    reading a few at a time.

  How to practice the rustiness away

  Typing from memory matters more than reading:

  - Each day, pick 2–3 modules from the lists above and write a 10-line
    throwaway script per module in a plain editor with autocomplete off, since
    CoderPad is close to that.
  - Write one tiny unittest file from scratch every time until the boilerplate
    comes without thinking.
  - Keep a one-page cheat sheet of signatures you forget, like seek/tell,
    asyncio.run and bisect, and rewrite it from memory before each session.

  The files run on Python 3.14 (based on __pycache__), so 3.11+ features like
  TaskGroup and asyncio.timeout are available. Some interview environments run
  older versions, so check what CoderPad uses.

✻ Worked for 39s · done 4:41 PM

---

Notes

Most backtracking solutions follow the same template:

def backtrack(state):
    if state is complete:
        return True

    for choice in available_choices:
        if choice is valid:
            make the choice
            if backtrack(state):
                return True
            undo the choice      # the "back" in backtracking

    return False

So you don't need to invent an algorithm each time. You only need to answer four questions:

1. Decision: What am I deciding at each step?
2. Choices: What are my options for that decision?
3. Validity: What makes an option allowed?
4. Undo: What do I need to restore when I back out?

-------
How to solve wordy coding problems:

Phase 1: Understand (before any algorithm)

Read twice. The first read is for the gist. On the second, annotate as you go: underline constraints, circle key verbs, and mark anything ambiguous.
Find the “what to return” sentence, usually near the end. Write down exactly what’s being asked and what’s being optimized (max, min, count, yes/no) and over what.
Strip the story. Rewrite the problem as one plain sentence with no characters or scenery: “Given X, return Y such that Z.”
Pin down input, output, and constraints:
Input: types and sizes
Output: type and what it represents (a value, an index, a list)
Constraints: ranges, sorted or not, contiguous or not, order preserved or not
Ask clarifying questions from a standard list: empty input, duplicates, negatives, ties, what to return if no answer exists, whether the input can be modified.

Phase 2: Verify understanding

Trace the given example by hand. Check that your understanding produces the same answer. If it doesn’t, you’ve found a misreading before writing any code.
Scan once more for buried details, such as tie-breaking rules, a sentence in the middle that adds a condition, and value versus index versus items.
State your understanding out loud to the interviewer and let them correct you.

Phase 3: Solve

Propose brute force first, with its complexity. It shows you understand the problem and often reveals where the inefficiency is.
Look for the pattern (two pointers, sliding window, hash map, binary search, BFS/DFS, and so on) using the constraints as hints. Input size of 10^5 rules out O(n²), for example.

Phase 4: Verify the code

Break the code into small named pieces so each can be tested alone.
Trace in layers with a table: variables as columns, one row per iteration, inner pieces verified separately and treated as black boxes in the outer trace.
Test the boundaries: the answer and the value just below it, the smallest input, and the extremes of the constraints.
Read each comparison in plain English (> vs >= and < vs <=) and check what each variable means at that line and what’s true when each loop ends.

If you only remember three of these, keep: find the “what to return” sentence, trace the example before coding, and trace your code on a small input after.