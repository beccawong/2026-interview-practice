"""
Credit / Token Balance Tracker with Expiration

Reported as a "credit tracking service for user token balances" and a
"usage-credit system with expiration rules".

Part 1 - Grants and balance
    add_credit(user_id, amount, timestamp, expires_at)
    get_balance(user_id, timestamp) -> int
    Credits only count when timestamp is in [granted timestamp, expires_at).

Part 2 - Spending
    spend(user_id, amount, timestamp)
    Spend from the credit grant that expires soonest first. Raise (and change
    nothing) if the available balance is insufficient.

Part 3 - Out-of-order events
    Calls may arrive out of timestamp order (e.g. a grant whose timestamp is
    earlier than a spend you've already processed). get_balance(user, t)
    must reflect only events at or before t. Consider storing an event log
    and replaying it rather than mutating balances directly.

Part 4 - Follow-ups to be ready to discuss
    - Many users, many grants: per-user heap ordered by expiry.
    - Concurrency: two spends for the same user at the same time.
    - Refunds / reversing a spend.
    - Precision: integers vs floats for currency-like values.

Sources:
    https://www.interviewquery.com/interview-guides/openai-software-engineer
    https://www.interviewquery.com/guides/openai-software-engineer?exp_page=2
    https://staffengprep.com/companies/openai/
"""
