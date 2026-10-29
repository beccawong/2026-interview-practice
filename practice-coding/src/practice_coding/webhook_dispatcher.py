"""
Webhook Dispatcher

Overlaps with task_queue_retries.py; consider building that first and
reusing it here.

Part 1 - Subscriptions and dispatch
    subscribe(event_type, url)
    publish(event_type, payload)
    Deliver the payload to every subscriber of that event type. Inject the
    HTTP sender as a function (send(url, payload) -> status_code) so tests
    can fake it.

Part 2 - Retries with backoff
    Retry failed deliveries (non-2xx or exception) with exponential backoff
    and jitter, up to N attempts. Inject a clock / sleep function so tests
    don't actually wait.

Part 3 - Dead-letter queue
    After N failed attempts, move the delivery to a dead-letter queue that
    can be inspected and replayed.

Part 4 - Concurrency
    Deliver to different subscribers concurrently (threads or asyncio), but
    keep deliveries to the same URL in order.

Part 5 - Follow-ups to be ready to discuss
    - Idempotency keys so receivers can dedupe retries.
    - Signing payloads (HMAC) so receivers can verify the sender.
    - One slow subscriber shouldn't block everyone else.

Sources:
    https://www.interviewquery.com/interview-guides/openai-software-engineer
    https://www.hellointerview.com/guides/openai/l5
"""
