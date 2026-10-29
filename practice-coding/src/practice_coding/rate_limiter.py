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
