# Events come in as (user_id, chat_id, timestamp)
# get_num_recent_interactions need to return the number between [T-14, T]
# A session is when user has interact event and not ended. A chat without any event within the window is considered not active

WINDOW = 15  # minutes

from collections import defaultdict, deque


# Notes afterwards
# Session count could have been a boolean as a session is either active or not. Don't need an int
# Read and understand the question. I didn't get time was relative to the event's timestamp
# Think about state before coding
class SessionTracker:
    def __init__(self):
        self.event_log : dict[tuple[str, int], deque] = defaultdict(deque)
        self.over_max_time = -1
        self.user_session_count: dict[tuple[str, int], int] = defaultdict(int)

    def _slide_window(self) -> None:
        min_time = self.over_max_time - WINDOW
        for k, v in self.event_log.items():
            while v and v[0][2] < min_time:
                v.popleft()
            if len(v) == 0:
                self.user_session_count[k] -= 1

    def process_event(self, user_id: str, chat_id: int, timestamp: int, event_type: str = "interact") -> None:
        key = (user_id, chat_id)
        if event_type == "end":
            print(f"decrementing {user_id} {chat_id} {event_type}")
            self.user_session_count[key] -= 1
        if event_type == "interact" and key not in self.user_session_count:
            print(f"incrementing {user_id} {chat_id} {event_type}")
            self.user_session_count[key] = 1
        
        self.over_max_time = max(timestamp, self.over_max_time)
        self.event_log[key].append((user_id, chat_id, timestamp, event_type))
        self._slide_window()
        
    def get_num_recent_interactions(self, user_id: str, chat_id: int) -> int:
        event_log = self.event_log[(user_id, chat_id)]
        return len(event_log)

    def get_active_session_count(self, user_id: str) -> int:
        result = 0
        for k, v in self.user_session_count.items():
            print(f"{user_id} k is {k}")
            print(f"{user_id} v is {v}")
            if k[0] == user_id:
                result += max(v, 0)
        return result


tr = SessionTracker()

# t = 0-10  ── three interactions across two chats
tr.process_event("u1", 1, 0, "interact")  # chat 1 – first interact
print(tr.get_active_session_count("u1"))      # 1

tr.process_event("u1", 1, 5, "end")  # chat 1 – second interact
print(tr.get_active_session_count("u1"))

tr.process_event("u1", 2, 10, "interact")  # chat 2 – first interact

assert tr.get_num_recent_interactions("u1", 1) == 2
assert tr.get_num_recent_interactions("u1", 2) == 1

# suppose u1 stopped interacting and we have processed events many from other users
tr.process_event("other", 99, 26, "interact")  # t = 24

assert tr.get_active_session_count("u1") == 0

assert tr.get_num_recent_interactions("u1", 1) == 0  # (chat 1 window expired)
assert tr.get_num_recent_interactions("u1", 2) == 1  # (chat 2 window not yet expired)

      # 0

class SessionTracker_after_option1:
    def __init__(self):
        self.now = -1
        self.events = defaultdict(deque)        # (user, chat) -> deque[ts]
        self.last_type = {}                     # (user, chat) -> "interact" | "end"
        self.chats_by_user = defaultdict(set)

    def _prune(self, key):
        q = self.events.get(key)
        while q and q[0] < self.now - (WINDOW - 1):
            q.popleft()
        return q

    def process_event(self, user_id, chat_id, ts, event_type="interact"):
        key = (user_id, chat_id)
        self.now = max(self.now, ts)
        self.events[key].append(ts)
        self.last_type[key] = event_type
        self.chats_by_user[user_id].add(chat_id)

    def get_num_recent_interactions(self, user_id, chat_id):
        q = self._prune((user_id, chat_id))
        return len(q) if q else 0

    def get_active_session_count(self, user_id):
        return sum(
            1 for c in self.chats_by_user.get(user_id, ())
            if self._prune((user_id, c)) and self.last_type[(user_id, c)] == "interact"
        )

class SessionTracker_after_option2:
    def __init__(self):
        self.window = deque()            # (key, ts), oldest first
        self.count = defaultdict(int)    # (user, chat) -> events in window
        self.last_type = {}              # (user, chat) -> type of latest event
        self.active = defaultdict(int)   # user -> active session count

    def _is_active(self, key):
        return self.count.get(key, 0) > 0 and self.last_type.get(key) == "interact"

    def _sync(self, key, was_active):
        if was_active != self._is_active(key):
            self.active[key[0]] += -1 if was_active else 1

    def process_event(self, user_id, chat_id, ts, event_type="interact"):
        key = (user_id, chat_id)

        was = self._is_active(key)
        self.window.append((key, ts))
        self.count[key] += 1
        self.last_type[key] = event_type
        self._sync(key, was)

        cutoff = ts - WINDOW + 1
        while self.window and self.window[0][1] < cutoff:
            old, _ = self.window.popleft()
            was = self._is_active(old)
            self.count[old] -= 1
            if self.count[old] == 0:
                del self.count[old], self.last_type[old]
            self._sync(old, was)

    def get_num_recent_interactions(self, user_id, chat_id):
        return self.count.get((user_id, chat_id), 0)

    def get_active_session_count(self, user_id):
        return self.active.get(user_id, 0)