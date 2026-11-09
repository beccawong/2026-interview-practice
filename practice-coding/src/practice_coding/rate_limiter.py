"""
Rate Limiter

Reported as a practical "utility" coding question. Inject the clock
(a now() -> float function) so tests are deterministic.

Part 1 - Fixed window
    allow(client_id) -> bool. At most N requests per client per window
    of W seconds.

Part 2 - Sliding window log
    Fix the burst problem at window boundaries (2N requests across the edge
    of two windows) by storing request timestamps in a deque per client.

Part 3 - Token bucket
    Capacity C, refill rate R tokens/sec, computed lazily on each call
    (no background thread). Compare memory and accuracy with Part 2.

Part 4 - Thread safety
    Many threads call allow() concurrently for the same client.

Part 5 - Follow-ups to be ready to discuss
    - Cleaning up state for clients that stopped sending requests.
    - Distributed rate limiting across servers (Redis, atomic increments).
    - Different limits per client tier; weighted requests (e.g. by token count).

Sources:
    https://www.interviewquery.com/interview-guides/openai-software-engineer
    https://www.interviewquery.com/guides/openai-software-engineer?exp_page=2
"""

import threading
import time
import unittest
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class TokenBucketRateLimiter:
    """Per-client token bucket.

    Each client gets a bucket holding up to `capacity` tokens, refilled
    continuously at `refill_rate` tokens/second. Refill is computed lazily on
    each call from the elapsed time, so there is no background thread.

    Memory is O(1) per client (two floats), versus O(N) timestamps per client
    for a sliding-window log. It allows bursts of up to `capacity`, then
    smooths to `refill_rate` on average.
    """

    def __init__(
        self,
        capacity: float,
        refill_rate: float,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        self._capacity = float(capacity)
        self._refill_rate = float(refill_rate)
        self._now = now
        self._buckets: dict[str, _Bucket] = {}
        # One lock for the dict and the buckets. Per-client locks would give
        # more concurrency, but the critical section is tiny.
        self._lock = threading.Lock()

    def _refill(self, bucket: _Bucket, now: float) -> None:
        # Clamp elapsed at 0 in case a non-monotonic clock goes backwards.
        elapsed = max(0.0, now - bucket.last_refill)
        bucket.tokens = min(self._capacity, bucket.tokens + elapsed * self._refill_rate)
        bucket.last_refill = now

    def allow(self, client_id: str, cost: float = 1.0) -> bool:
        """Consume `cost` tokens for `client_id` if available."""
        if cost <= 0:
            raise ValueError("cost must be positive")
        if cost > self._capacity:
            return False  # Can never be satisfied.
        with self._lock:
            now = self._now()
            bucket = self._buckets.get(client_id)
            if bucket is None:
                bucket = _Bucket(tokens=self._capacity, last_refill=now)
                self._buckets[client_id] = bucket
            else:
                self._refill(bucket, now)
            if bucket.tokens >= cost:
                bucket.tokens -= cost
                return True
            return False

    def tokens(self, client_id: str) -> float:
        """Tokens currently available to `client_id` (full if unseen)."""
        with self._lock:
            bucket = self._buckets.get(client_id)
            if bucket is None:
                return self._capacity
            self._refill(bucket, self._now())
            return bucket.tokens

    def retry_after(self, client_id: str, cost: float = 1.0) -> float:
        """Seconds until `cost` tokens are available (0 if available now)."""
        missing = cost - self.tokens(client_id)
        return max(0.0, missing / self._refill_rate)

    def cleanup(self) -> int:
        """Drop buckets that have refilled to full; returns how many were dropped.

        A full bucket is indistinguishable from a brand-new one, so removing
        it is lossless. Call periodically to bound memory for idle clients.
        """
        with self._lock:
            now = self._now()
            idle = []
            for client_id, bucket in self._buckets.items():
                self._refill(bucket, now)
                if bucket.tokens >= self._capacity:
                    idle.append(client_id)
            for client_id in idle:
                del self._buckets[client_id]
            return len(idle)

    def __len__(self) -> int:
        with self._lock:
            return len(self._buckets)


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


class TokenBucketRateLimiterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.limiter = TokenBucketRateLimiter(capacity=3, refill_rate=1, now=self.clock)

    def test_allows_burst_up_to_capacity(self):
        self.assertEqual([self.limiter.allow("a") for _ in range(4)], [True, True, True, False])

    def test_refills_over_time(self):
        for _ in range(3):
            self.limiter.allow("a")
        self.assertFalse(self.limiter.allow("a"))
        self.clock.advance(1)
        self.assertTrue(self.limiter.allow("a"))
        self.assertFalse(self.limiter.allow("a"))

    def test_partial_refill_accumulates(self):
        for _ in range(3):
            self.limiter.allow("a")
        self.clock.advance(0.5)
        self.assertFalse(self.limiter.allow("a"))
        self.clock.advance(0.5)
        self.assertTrue(self.limiter.allow("a"))

    def test_refill_capped_at_capacity(self):
        self.limiter.allow("a")
        self.clock.advance(1000)
        self.assertEqual(self.limiter.tokens("a"), 3)
        self.assertEqual([self.limiter.allow("a") for _ in range(4)], [True, True, True, False])

    def test_clients_are_independent(self):
        for _ in range(3):
            self.limiter.allow("a")
        self.assertFalse(self.limiter.allow("a"))
        self.assertTrue(self.limiter.allow("b"))

    def test_weighted_cost(self):
        self.assertTrue(self.limiter.allow("a", cost=2))
        self.assertFalse(self.limiter.allow("a", cost=2))
        self.assertTrue(self.limiter.allow("a", cost=1))

    def test_denied_request_does_not_consume(self):
        self.limiter.allow("a", cost=2)
        self.assertFalse(self.limiter.allow("a", cost=2))
        self.assertAlmostEqual(self.limiter.tokens("a"), 1)

    def test_cost_above_capacity_never_allowed(self):
        self.assertFalse(self.limiter.allow("a", cost=4))
        self.assertEqual(self.limiter.tokens("a"), 3)

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            TokenBucketRateLimiter(capacity=0, refill_rate=1)
        with self.assertRaises(ValueError):
            TokenBucketRateLimiter(capacity=1, refill_rate=0)
        with self.assertRaises(ValueError):
            self.limiter.allow("a", cost=0)

    def test_retry_after(self):
        self.assertEqual(self.limiter.retry_after("a"), 0)
        for _ in range(3):
            self.limiter.allow("a")
        self.assertAlmostEqual(self.limiter.retry_after("a"), 1)
        self.assertAlmostEqual(self.limiter.retry_after("a", cost=2), 2)

    def test_clock_going_backwards_does_not_drain(self):
        self.clock.t = 10
        self.limiter.allow("a")
        self.clock.t = 5
        self.assertAlmostEqual(self.limiter.tokens("a"), 2)

    def test_cleanup_removes_only_full_buckets(self):
        self.limiter.allow("a")
        self.clock.advance(0.5)
        self.limiter.allow("b")
        self.clock.advance(0.6)  # a is full again, b is not
        self.assertEqual(self.limiter.cleanup(), 1)
        self.assertEqual(len(self.limiter), 1)
        self.assertLess(self.limiter.tokens("b"), 3)

    def test_thread_safety_no_over_admission(self):
        # Frozen clock: exactly `capacity` requests may succeed in total.
        limiter = TokenBucketRateLimiter(capacity=100, refill_rate=1, now=FakeClock())
        allowed = 0
        allowed_lock = threading.Lock()
        barrier = threading.Barrier(16)

        def worker():
            nonlocal allowed
            barrier.wait()
            local = sum(limiter.allow("shared") for _ in range(50))
            with allowed_lock:
                allowed += local

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(allowed, 100)

    def test_default_clock_works(self):
        limiter = TokenBucketRateLimiter(capacity=1, refill_rate=1)
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))


if __name__ == "__main__":
    unittest.main()
