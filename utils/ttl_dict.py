import time
import threading
from typing import List
from config.rag_config import rag_config

class ChatHistDict(dict):
    """
    Structure:
    user: str -> List[msg: str]
    """

    def __init__(self, default_ttl=None):
        super().__init__()
        self.default_ttl = default_ttl or rag_config.CHAT_HISTORY_TTL # in seconds
        self.expire_times = {}
        self.data = {}
        self.lock = threading.Lock()  # Ensure thread-safety
        self._start_timer()

    def _start_timer(self):
        """Starts a background thread to periodically check for expired keys."""
        thread = threading.Thread(target=self._check_expirations, daemon=True)
        thread.start()

    def _check_expirations(self):
        """Periodically checks for and removes expired keys."""
        while True:
            with self.lock:
                now = time.time()
                for key, messages in self.items():
                    msgs = [(m, t) for m, t in messages if t < now]
                    self[key] = msgs
            time.sleep(60)  # Check every min (adjust as needed)

    def add(self, user, msg, ttl=None):
        with self.lock:
            if user not in self:
                self[user] = []
            self[user].append((msg, ttl or self.default_ttl))

    def set(self, user: str, messages: List[str]) -> None:
        with self.lock:
            now = time.time()
            self[user] = [(m, now) for m in messages]

    def get(self, user: str, default=None):
        with self.lock:
            if user in self:
                return [_[0] for _ in self[user]]
            else:
                return default
