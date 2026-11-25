"""Bookmarks: one marked page per manga, so you can pick up where you wanted to."""
import json
import threading
import time

from config import PROJECT_ROOT

BOOKMARKS_FILE = PROJECT_ROOT / "bookmarks.json"
_lock = threading.Lock()


def read_all():
  """{folder path: {"author": ..., "manga": ..., "page": 0-based page index, "added": unix time}}

  Older entries have no "page" (the whole manga was bookmarked): callers treat that as the first chapter.
  """
  try:
    data = json.loads(BOOKMARKS_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}
  except (OSError, ValueError):
    return {}


def get(folder, data=None):
  """The bookmark entry of this manga, or None."""
  return (read_all() if data is None else data).get(str(folder.resolve()))


def is_marked(folder, data=None):
  return get(folder, data) is not None


def set_marked(folder, author, manga, on, page=0):
  """Bookmark `page` (0-based index) of a manga, moving the bookmark if it already exists. on=False removes it."""
  with _lock:
    data = read_all()
    key = str(folder.resolve())
    if on:
      added = data.get(key, {}).get("added", time.time())
      data[key] = {"author": author, "manga": manga, "page": int(page), "added": added}
    else:
      data.pop(key, None)
    try:
      BOOKMARKS_FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
      pass