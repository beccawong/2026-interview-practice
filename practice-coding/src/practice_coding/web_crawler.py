"""
Web Crawler

Builds on breadth_first_search.py and in_memory_concurrent_worker_pool.py.

Part 1 - Single-threaded crawl
    crawl(start_url, fetch_links) -> set[str]
    fetch_links(url) -> list[str] is injected; in tests it reads from a
    dict-based fake link graph. Only follow URLs on the same hostname as
    start_url. Never visit a URL twice (the graph has cycles).

Part 2 - Limits
    Add max_depth and max_pages limits.

Part 3 - Concurrent crawl
    Same result, but fetch pages concurrently with a fixed number of workers
    (threads or asyncio). Make the visited set safe to use from multiple
    workers. The tricky part: knowing when the crawl is finished (queue is
    empty AND no worker is still fetching).

Part 4 - Follow-ups to be ready to discuss
    - Per-host rate limiting (reuse rate_limiter.py).
    - URL normalization (trailing slashes, fragments, query param order).
    - Fetch timeouts and retries for slow or failing pages.
    - Scaling across machines: partition the URL space by hash.

Sources:
    https://www.1point3acres.com/interview/thread/1149658
    https://igotanoffer.com/en/advice/openai-coding-interview
"""
