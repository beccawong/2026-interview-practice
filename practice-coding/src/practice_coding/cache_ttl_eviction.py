import heapq
import time
import unittest
from unittest.mock import patch


class TtlCache[K,V]:
    def __init__(self, ttl_in_sec: int):
        self.data: dict[K, tuple[V, float]] = {}
        self.most_recently_used_with_time = []
        self.ttl_in_sec = ttl_in_sec

    def put(self, key: K, value: V):
        self.evict()

        expiration = time.time() + self.ttl_in_sec
        self.data[key] = (value, expiration)
        heapq.heappush(self.most_recently_used_with_time, (expiration, key))

    def get(self, key: K) -> V | None:
        self.evict()

        result = self.data.get(key, None)
        if result:
            now = time.time()
            if result[1] <= now:
                del self.data[key]
                return None
            
            expiration = now + self.ttl_in_sec
            self.data[key] = (result[0], expiration)
            heapq.heappush(self.most_recently_used_with_time, (expiration, key))
            return result[0]
        return None

    def evict(self):
        now = time.time()
        while self.most_recently_used_with_time and self.most_recently_used_with_time[0][0] <= now:
            expired_item = heapq.heappop(self.most_recently_used_with_time)
            if expired_item[1] in self.data and self.data[expired_item[1]][1] <= now:
                del self.data[expired_item[1]]


class TtlCacheTest(unittest.TestCase):

    def test_insert(self):
        cache = TtlCache(5)
        cache.put("first", 1)
        self.assertEqual(cache.get("first"), 1)

    @patch("time.time")
    def test_expiration(self, mock_time):
        mock_time.return_value = 10
        cache = TtlCache(1)
        cache.put("test_expiration", 3)
        self.assertEqual(cache.get("test_expiration"), 3)
        mock_time.return_value = 1000
        self.assertIsNone(cache.get("test_expiration"))

if __name__ == "__main__":
    unittest.main()
