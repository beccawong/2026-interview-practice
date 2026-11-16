import random
import sys
import threading
import unittest
from collections.abc import Callable

from practice_coding.lru_cache import LRUCache

NUM_THREADS = 8
OPS_PER_THREAD = 5_000


def setUpModule() -> None:
    """Force the interpreter to switch threads very often so races surface."""
    global _original_switch_interval
    _original_switch_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)


def tearDownModule() -> None:
    sys.setswitchinterval(_original_switch_interval)


def run_concurrently(worker: Callable[[int], None], num_threads: int = NUM_THREADS) -> None:
    """Start all workers at the same instant and re-raise any exception they hit."""
    barrier = threading.Barrier(num_threads)
    errors: list[BaseException] = []

    def wrapped(thread_id: int) -> None:
        barrier.wait()
        try:
            worker(thread_id)
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=wrapped, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        if t.is_alive():
            raise AssertionError("worker thread hung (possible deadlock)")
    if errors:
        raise errors[0]


class LRUCacheThreadSafetyTest(unittest.TestCase):
    def assert_still_behaves_like_lru(self, cache: LRUCache, capacity: int, old_keys: list[str]) -> None:
        """After concurrent use, the cache must still behave correctly through its public API.

        Corruption from a race shows up here: entries that never get evicted leave old keys
        behind or push size() above capacity, dangling nodes raise on eviction, and a broken
        ordering evicts the wrong key.
        """
        self.assertLessEqual(cache.size(), capacity)

        # Flush: `capacity` fresh keys must evict every entry written during the concurrent phase.
        fresh = [f"__fresh{i}" for i in range(capacity)]
        for i, key in enumerate(fresh):
            cache.add(key, i)
        self.assertEqual(cache.size(), capacity)
        for key in old_keys:
            self.assertIsNone(cache.get(key), f"{key} survived a full flush")
        for i, key in enumerate(fresh):
            self.assertEqual(cache.get(key), i)

        # Recency still works: touch the oldest key, then the next-oldest is evicted instead.
        cache.get(fresh[0])
        cache.add("__extra", -1)
        self.assertEqual(cache.size(), capacity)
        self.assertEqual(cache.get(fresh[0]), 0)
        if capacity > 1:
            self.assertIsNone(cache.get(fresh[1]))
        self.assertEqual(cache.get("__extra"), -1)

    def test_concurrent_adds_of_distinct_keys_respect_capacity(self) -> None:
        capacity = 50
        cache: LRUCache[int] = LRUCache(capacity)

        def worker(thread_id: int) -> None:
            for i in range(OPS_PER_THREAD):
                cache.add(f"t{thread_id}-k{i}", i)

        run_concurrently(worker)

        self.assertEqual(cache.size(), capacity)
        written = [f"t{t}-k{i}" for t in range(NUM_THREADS) for i in range(OPS_PER_THREAD)]
        self.assert_still_behaves_like_lru(cache, capacity, written)

    def test_concurrent_mixed_get_and_add_keeps_structure_consistent(self) -> None:
        capacity = 20
        cache: LRUCache[int] = LRUCache(capacity)
        keys = [f"k{i}" for i in range(100)]  # more keys than capacity -> constant eviction

        def worker(thread_id: int) -> None:
            rng = random.Random(thread_id)
            for _ in range(OPS_PER_THREAD):
                key = rng.choice(keys)
                if rng.random() < 0.5:
                    cache.add(key, rng.randint(0, 1_000))
                else:
                    cache.get(key)

        run_concurrently(worker)

        self.assert_still_behaves_like_lru(cache, capacity, keys)

    def test_size_never_observed_above_capacity(self) -> None:
        """add() briefly holds capacity + 1 entries before evicting; readers must never see that."""
        capacity = 10
        cache: LRUCache[int] = LRUCache(capacity)
        stop = threading.Event()
        observed_max = 0

        def observer() -> None:
            nonlocal observed_max
            while not stop.is_set():
                observed_max = max(observed_max, cache.size())

        def worker(thread_id: int) -> None:
            for i in range(OPS_PER_THREAD):
                cache.add(f"t{thread_id}-k{i}", i)

        watcher = threading.Thread(target=observer)
        watcher.start()
        try:
            run_concurrently(worker)
        finally:
            stop.set()
            watcher.join()

        self.assertLessEqual(observed_max, capacity)

    def test_concurrent_writes_to_same_key_last_write_is_one_of_the_writers(self) -> None:
        capacity = 5
        cache: LRUCache[tuple[int, int]] = LRUCache(capacity)

        def worker(thread_id: int) -> None:
            for i in range(OPS_PER_THREAD):
                cache.add("shared", (thread_id, i))

        run_concurrently(worker)

        self.assertEqual(cache.size(), 1)
        result = cache.get("shared")
        assert result is not None
        thread_id, i = result
        self.assertIn(thread_id, range(NUM_THREADS))
        self.assertEqual(i, OPS_PER_THREAD - 1)  # each thread's final write is its last i
        self.assert_still_behaves_like_lru(cache, capacity, ["shared"])

    def test_get_returns_only_values_that_were_written_for_that_key(self) -> None:
        """Readers must never see a value belonging to a different key (torn update)."""
        capacity = 8
        cache: LRUCache[str] = LRUCache(capacity)
        keys = [f"k{i}" for i in range(16)]

        def worker(thread_id: int) -> None:
            rng = random.Random(thread_id)
            for _ in range(OPS_PER_THREAD):
                key = rng.choice(keys)
                if thread_id % 2 == 0:
                    cache.add(key, f"{key}:{rng.randint(0, 99)}")
                else:
                    value = cache.get(key)
                    if value is not None and not value.startswith(f"{key}:"):
                        raise AssertionError(f"get({key!r}) returned {value!r}")

        run_concurrently(worker)

        self.assert_still_behaves_like_lru(cache, capacity, keys)


if __name__ == "__main__":
    unittest.main()
