"""
Set

A hash set built on separate chaining, without using the built-in set or dict.

    add, discard, remove, in    O(1) average, O(n) if every item collides
    resize                      O(n), but O(1) amortized per add
    iteration                   O(capacity + n), in no guaranteed order

The hash table is written by hand. MutableSet supplies the operations that can
be expressed in terms of it: remove, pop, |, &, -, ^, <=, ==, isdisjoint.
"""

from collections.abc import Hashable, Iterable, Iterator, MutableSet

INITIAL_CAPACITY = 8
MAX_LOAD_FACTOR = 0.75


class HashSet[T: Hashable](MutableSet[T]):
    def __init__(self, items: Iterable[T] = ()) -> None:
        self._buckets: list[list[T]] = [[] for _ in range(INITIAL_CAPACITY)]
        self._size = 0
        for item in items:
            self.add(item)

    def _bucket_for(self, item: object) -> list[T]:
        # Python's % keeps the index non-negative even when the hash is negative.
        return self._buckets[hash(item) % len(self._buckets)]

    def __contains__(self, item: object) -> bool:
        # Checking identity first matches the built-in set, so that a NaN
        # (which is not equal to itself) can still be found.
        return any(x is item or x == item for x in self._bucket_for(item))

    def __iter__(self) -> Iterator[T]:
        for bucket in self._buckets:
            yield from bucket

    def __len__(self) -> int:
        return self._size

    def __repr__(self) -> str:
        return f"HashSet({list(self)!r})"

    def add(self, item: T) -> None:
        if item in self:
            return
        if (self._size + 1) / len(self._buckets) > MAX_LOAD_FACTOR:
            self._resize()
        self._bucket_for(item).append(item)
        self._size += 1

    def discard(self, item: T) -> None:
        bucket = self._bucket_for(item)
        for i, x in enumerate(bucket):
            if x is item or x == item:
                # Order within a bucket doesn't matter, so swap and pop in O(1).
                bucket[i] = bucket[-1]
                bucket.pop()
                self._size -= 1
                return

    def clear(self) -> None:
        # The inherited clear() pops one at a time, rescanning empty buckets.
        self._buckets = [[] for _ in range(INITIAL_CAPACITY)]
        self._size = 0

    def _resize(self) -> None:
        old_buckets = self._buckets
        self._buckets = [[] for _ in range(len(old_buckets) * 2)]
        for bucket in old_buckets:
            for item in bucket:
                self._bucket_for(item).append(item)


class _Collides:
    """Every instance lands in the same bucket, to exercise chaining."""

    def __init__(self, val: int) -> None:
        self.val = val

    def __hash__(self) -> int:
        return 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Collides) and self.val == other.val


if __name__ == "__main__":
    # add, contains, and duplicates
    s = HashSet([1, 2, 2, 3])
    assert len(s) == 3
    assert 2 in s and 4 not in s

    # discard is a no-op when missing, remove raises
    s.discard(99)
    s.discard(2)
    assert 2 not in s and len(s) == 2
    try:
        s.remove(2)
        raise AssertionError("expected KeyError")
    except KeyError:
        pass

    # growth keeps every item reachable
    big = HashSet(range(1000))
    assert len(big) == 1000
    assert len(big._buckets) > INITIAL_CAPACITY
    assert all(i in big for i in range(1000))
    assert sorted(big) == list(range(1000))

    # hash collisions, including removing from the middle of a chain
    chain = HashSet(_Collides(i) for i in range(5))
    assert len(chain) == 5
    chain.discard(_Collides(2))
    assert _Collides(2) not in chain
    assert all(_Collides(i) in chain for i in (0, 1, 3, 4))

    # negative hashes, and values that compare equal across types
    assert -1 in HashSet([-1, -2])
    assert len(HashSet([1, 1.0, True])) == 1

    # NaN is only found by identity, the same as the built-in set
    nan = float("nan")
    assert nan in HashSet([nan])
    assert float("nan") not in HashSet([nan])

    # unhashable items are rejected
    try:
        HashSet([[1]])
        raise AssertionError("expected TypeError")
    except TypeError:
        pass

    # set algebra and comparisons inherited from MutableSet
    a, b = HashSet([1, 2, 3]), HashSet([2, 3, 4])
    assert a | b == HashSet([1, 2, 3, 4])
    assert a & b == HashSet([2, 3])
    assert a - b == HashSet([1])
    assert a ^ b == HashSet([1, 4])
    assert HashSet([2, 3]) <= a
    assert isinstance(a | b, HashSet)

    # pop empties the set, then raises
    p = HashSet([1, 2])
    assert {p.pop(), p.pop()} == {1, 2}
    try:
        p.pop()
        raise AssertionError("expected KeyError")
    except KeyError:
        pass

    # clear leaves the set usable
    big.clear()
    assert len(big) == 0 and list(big) == []
    big.add(1)
    assert 1 in big

    print("all passed")
