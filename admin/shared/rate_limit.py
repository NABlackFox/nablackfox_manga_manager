"""Keeps requests spaced out so the API's per-minute limits are never exceeded."""
import threading
import time


class RateLimiter:
  """Allows `per_minute` calls a minute by spacing them evenly. Thread-safe."""

  def __init__(self, per_minute, clock=time.monotonic, sleep=time.sleep):
    self.interval = 60.0 / max(1, per_minute)
    self._clock = clock
    self._sleep = sleep
    self._next = 0.0
    self._lock = threading.Lock()

  def wait(self):
    """Block until this call is allowed to go out."""
    with self._lock:
      now = self._clock()
      start = max(now, self._next)
      self._next = start + self.interval
    delay = start - now
    if delay > 0:
      self._sleep(delay)
