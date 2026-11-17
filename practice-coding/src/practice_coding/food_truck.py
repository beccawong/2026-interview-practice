# Problem: The Food Truck Festival

# A food truck at a weekend festival keeps a log of every order it takes, in the order the orders came in. Each order is for exactly one item from the menu, and each item is labeled with a number (for example, 1 for tacos, 2 for burritos, 3 for churros, and so on).

# The owner wants to understand the busiest “simple” stretch of the day. Staff can only keep a small number of items in the prep station at once, so a stretch is called simple if the orders in it use at most two different items. The stretch has to be a run of orders that came one right after another, with no gaps or reordering.

# The owner wants to know: what’s the longest simple stretch in the log? Return how many orders are in it.

# For example, if the log is [1, 2, 1, 2, 3, 3], the stretch [1, 2, 1, 2] uses only items 1 and 2 and has 4 orders. The stretch [2, 3, 3] has 3 orders. No simple stretch is longer than 4, so the answer is 4.

# The log can contain up to 100,000 orders. Item labels are integers between 0 and 10,000. The log has at least one order.