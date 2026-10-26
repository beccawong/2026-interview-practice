from collections import deque
from dataclasses import dataclass


@dataclass(eq=False)
class Node[V]:
    value: V
    neighbors: list[Node]

def search[V](start_node: Node[V], search_value: V) -> Node[V] | None:
    visited = set()
    to_visit = [start_node]
    while(len(to_visit) > 0):
        current_node = to_visit.pop()
        if current_node in visited:
            continue
        if current_node.value == search_value:
            return current_node
        
        visited.add(current_node)
        to_visit.extend(current_node.neighbors)
    return None

def search_recursive[V](start_node: Node[V], search_value: V) -> Node[V] | None:

# n5 = Node(5, [])
# n4 = Node(4, [])
n3 = Node(3, [])
n2 = Node(2, [n3])
n1 = Node(1, [n3])
n0 = Node(0, [n1, n2])

print(search(n0, 3))
print(search(n0, 10))
