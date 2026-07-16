"""uny-x utilities — delays, rate limiting, tweet ID extraction."""

import random
import re
import time
from pathlib import Path

MIN_DELAY = 0.2   # 200ms
MAX_DELAY = 3.0   # 3s


def random_delay(min_s: float = MIN_DELAY, max_s: float = MAX_DELAY) -> None:
    """Sleep a random interval to mimic human timing."""
    time.sleep(random.uniform(min_s, max_s))


_TWEET_URL_RE = re.compile(
    r'(?:https?://)?(?:www\.)?(?:x\.com|twitter\.com)/\w+/status/(\d+)'
)


def extract_tweet_id(value: str) -> str:
    """Return a tweet ID from a URL or raw ID string."""
    m = _TWEET_URL_RE.search(value)
    if m:
        return m.group(1)
    if value.isdigit():
        return value
    raise ValueError(f"Can't extract tweet ID from: {value}")


_USERNAME_RE = re.compile(r'^@?(\w{1,15})$')


def extract_username(value: str) -> str:
    """Normalise a handle: strip '@' prefix."""
    m = _USERNAME_RE.match(value)
    if m:
        return m.group(1)
    raise ValueError(f"Invalid username: {value}")


class RateLimitHandler:
    """Exponential backoff with jitter for rate limits and cooldowns."""

    def __init__(self, base_delay: float = 5.0, max_delay: float = 300.0):
        self._base = base_delay
        self._max = max_delay
        self._attempt = 0

    def wait(self) -> None:
        """Sleep with exponential backoff + jitter."""
        self._attempt += 1
        delay = min(self._base * (2 ** (self._attempt - 1)), self._max)
        jitter = random.uniform(0, 0.5 * delay)
        total = delay + jitter
        time.sleep(total)

    def reset(self) -> None:
        self._attempt = 0

    @property
    def attempt(self) -> int:
        return self._attempt
