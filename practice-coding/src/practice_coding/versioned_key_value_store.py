"""
Versioned (Time-Based) Key-Value Store

One of the most-cited OpenAI coding questions.

Part 1 - Basic versioned store
    set(key, value, timestamp)
    get(key, timestamp) -> the value with the largest timestamp <= the given
    timestamp, or None. Assume timestamps per key arrive increasing; use
    binary search (bisect) for get.

Part 2 - Out-of-order writes
    Timestamps for a key may arrive in any order. Keep each key's versions
    sorted on insert.

Part 3 - Persistence
    Save the store to disk and load it back (e.g. an append-only log file
    replayed on startup).

Part 4 - Thread safety
    Multiple threads call set/get concurrently. Start with one lock, then
    discuss per-key locks or a readers-writer lock.

Part 5 - Follow-ups to be ready to discuss
    - delete(key, timestamp) as a tombstone version.
    - Bounding memory: keep only the last N versions or a TTL.
    - Using a real clock instead of caller-supplied timestamps.

Sources:
    https://www.interviewquery.com/interview-guides/openai-software-engineer
    https://www.hellointerview.com/guides/openai/l5
    https://www.coditioning.com/blog/14/open-ai-swe-coding-interviewquestions-actual-questions-real-candidates
"""
