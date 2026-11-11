# Problem: The Warehouse Shift

# A logistics company runs a large warehouse where packages arrive on a conveyor belt throughout the day. Each package has a weight, and the packages are listed in the exact order they arrive. Because of safety rules, packages must be loaded onto trucks in that same arrival order, and a package can’t be split across trucks.

# The company has been told it must ship everything within a fixed number of days, and exactly one truck leaves per day. Each day, workers load some number of consecutive packages onto that day’s truck, in order, and the truck can’t carry more than its weight capacity. A day can’t be skipped, and every package must ship by the end of the final day.

# Management doesn’t want to buy a bigger truck than necessary, since capacity is expensive. They’re asking: what is the smallest truck capacity that would still let the warehouse ship every package within the allowed number of days?

# For example, suppose the weights, in arrival order, are [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] and the warehouse has 5 days. A truck with capacity 15 works: Day 1 loads 1, 2, 3, 4, 5, Day 2 loads 6, 7, Day 3 loads 8, Day 4 loads 9, and Day 5 loads 10. Capacity 14 would not be enough.

# The number of packages can be up to 50,000, each weight is between 1 and 500, and the number of days is at least 1.

def find_min_truck(weights: list[int], days: int) -> int:
    min_weight = max(weights)
    max_weight = 0
    for w in weights:
        max_weight += w

    left = min_weight
    right = max_weight

    while left < right:
        mid = left + ((right - left) // 2)
        running_sum = 0
        trucks_used = 1
        i = 0
        while i < len(weights) and trucks_used <= days:
            w = weights[i]
            if running_sum + w <= mid:
                running_sum += w
            else:
                trucks_used += 1
                running_sum = w
            i += 1

        if trucks_used > days:
            left = mid + 1
        else:
            right = mid
    return left


# weights = [3, 2, 2, 4], days = 2, answer is 6
# left  right   mid (capacity)  can_ship(mid)
# 4     11      7               yes
# 4     7       5               no
# 5     7       6               yes
# 6     6                       
# return 6