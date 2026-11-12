

class Node[T]:
    def __init__(self, key: str, value: None|T):
        self.key = key
        self.value = value
        self.prev = self
        self.next = self

    def __repr__(self) -> str:
        return f"Node({self.key}, {self.value}, prev: {self.prev.key}, next: {self.next.key}"



class LRUCache[T]:
    def __init__(self, capacity):
        self.capacity = capacity
        self.data: dict[str, Node[T]] = {}
        self.head: Node[T] = Node("__head__", None)
        self.tail: Node[T] = Node("__tail__", None)
        self.head.next = self.tail
        self.tail.prev = self.head

    def _move_node_to_front(self, node_to_move: Node[T]):
        self._remove(node_to_move)
        node_to_move.next = self.head.next
        node_to_move.prev = self.head
        self.head.next.prev = node_to_move
        self.head.next = node_to_move

    def _remove(self, node: Node[T]):
        node.prev.next = node.next
        node.next.prev = node.prev
        node.next = node
        node.prev = node


    def add(self, key: str, value: T) -> None:
        node = self.data.get(key)
        if node is None:
            node = Node(key, value)
            self.data[key] = node
        else:
            node.value = value

        self._move_node_to_front(node)
        if self.size() > self.capacity:
            to_remove = self.tail.prev
            self._remove(to_remove)
            del self.data[to_remove.key]
        

    def get(self, key: str) -> T | None:
        if key not in self.data:
            return None
        value_node = self.data[key]
        self._move_node_to_front(value_node)
        return value_node.value

    def size(self) -> int:
        return len(self.data)

    def debug(self):
        print(f"data: {self.data}")
        print(f"head: {self.head}")
        print(f"tail: {self.tail}")
        print(f"size: {self.size()}")
    

cache = LRUCache(1)
cache.add("a", 1)
cache.debug()
cache.add("b", 2)
cache.debug()
cache.add("a", 3)
cache.debug()