from collections import deque
from dataclasses import dataclass


@dataclass(eq=False)
class Node[V]:
    val: V
    neighbors: list[Node[V]]

def search[V](start_node: Node[V], search_value: V) -> Node[V] | None:
    to_visit = deque([start_node])
    visited = set(to_visit)

    while to_visit:
        current_node = to_visit.popleft()
        if current_node.val == search_value:
            return current_node
        for n in current_node.neighbors:
            if n not in visited:
                visited.add(n)
                to_visit.append(n)
    return None

nodes = [0,1,2,3,4,5,6]

def build_tree(values: list[int]) -> Node[int]:
    root = Node(values[0], [])
    parents = deque()
    next_parent = root
    for v in values[1:]:
        if len(next_parent.neighbors) == 2:
            next_parent = parents.popleft()
        new_node = Node(v, [])
        next_parent.neighbors.append(new_node)
        parents.append(new_node)

    return root

if __name__ == "__main__":
    n = build_tree(nodes)
    result = search(n, 9)
    print(result.val if result else None)
    result = search(n, 0)
    print(result.val if result else None)
    assert [c.val for c in build_tree([0,1,2,3,4,5,6]).neighbors] == [1, 2]
    a, b = Node("A", []), Node("B", [])
    a.neighbors, b.neighbors = [b], [a]
    assert search(a, "Z") is None   # hangs today
