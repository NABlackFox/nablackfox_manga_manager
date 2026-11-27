"""The one place that talks to the nhentai API.

Every request: carries the API key (Authorization: Key ...), a descriptive User-Agent, waits for its
rate-limit slot first, and retries politely on 429 / 5xx. The key is never put in an error message.
"""
import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

from admin.shared.rate_limit import RateLimiter

MAX_RETRIES = 4
MAX_WAIT_SECONDS = 120
TIMEOUT_SECONDS = 30


class ApiError(Exception):
  """A problem the person can understand. `status` is the HTTP status (0 = no connection)."""

  def __init__(self, message, status=0):
    super().__init__(message)
    self.status = status


class Client:
  def __init__(self, base, key, user_agent, limits_per_minute, sleep=time.sleep, opener=urllib.request.urlopen):
    self.base = base.rstrip("/")
    self._key = key
    self.user_agent = user_agent
    self._sleep = sleep
    self._opener = opener
    self._limiters = {group: RateLimiter(rate, sleep=sleep) for group, rate in limits_per_minute.items()}

  @property
  def has_key(self):
    return bool(self._key)

  def request(self, method, path, params=None, group="detail"):
    """Call the API and return the decoded JSON. Raises ApiError."""
    if not self._key:
      raise ApiError("No API key. Add NHENTAI_API_KEY=... to the .env file and restart.", 401)

    url = self.base + path
    if params:
      url += "?" + urlencode(params)
    request = urllib.request.Request(url, method=method, data=b"" if method == "POST" else None, headers={
        "Authorization": f"Key {self._key}",
        "User-Agent": self.user_agent,
        "Accept": "application/json",
    })
    limiter = self._limiters.get(group) or self._limiters["detail"]

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
      limiter.wait()
      try:
        with self._opener(request, timeout=TIMEOUT_SECONDS) as response:
          body = response.read()
        return json.loads(body) if body else {}
      except urllib.error.HTTPError as error:
        status = error.code
        detail = self._detail(error)
        if status == 429 or status >= 500:
          last_error = ApiError(f"The site answered {status}{': ' + detail if detail else ''}", status)
          self._sleep(min(self._retry_after(error, attempt), MAX_WAIT_SECONDS))
          continue
        if status in (401, 403):
          raise ApiError(f"The API refused this request ({status}). Check the API key and that it may do this"
                         f"{': ' + detail if detail else ''}", status) from None
        if status == 404:
          raise ApiError("Not found on the site.", 404) from None
        raise ApiError(f"The site answered {status}{': ' + detail if detail else ''}", status) from None
      except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
        last_error = ApiError(f"Could not reach the site ({getattr(error, 'reason', error)}).")
        self._sleep(min(2 ** attempt * 2, MAX_WAIT_SECONDS))
      except ValueError:
        raise ApiError("The site sent something that is not JSON.") from None
    raise last_error

  @staticmethod
  def _retry_after(error, attempt):
    header = error.headers.get("Retry-After") if error.headers else None
    try:
      return max(1.0, float(header))
    except (TypeError, ValueError):
      return 5.0 * 2 ** attempt   # no hint: back off 5s, 10s, 20s, ...

  @staticmethod
  def _detail(error):
    try:
      data = json.loads(error.read() or b"{}")
    except (ValueError, OSError):
      return ""
    if isinstance(data, dict):
      for key in ("detail", "error", "message"):
        value = data.get(key)
        if isinstance(value, str):
          return value[:200]
    return ""
