"""Bookmarks: the manga you plan to read next. Whole manga only, no page numbers."""
import json
import threading
import time

from config import PROJECT_ROOT

BOOKMARKS_FILE = PROJECT_ROOT / "bookmarks.json"
_lock = threading.Lock()


def read_all():
  """{folder path: {"author": ..., "manga": ..., "added": unix time}}"""
  try:
    data = json.loads(BOOKMARKS_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}
  except (OSError, ValueError):
    return {}


def is_marked(folder, data=None):
  return str(folder.resolve()) in (read_all() if data is None else data)


def set_marked(folder, author, manga, on):
  with _lock:
    data = read_all()
    key = str(folder.resolve())
    if on:
      data.setdefault(key, {"author": author, "manga": manga, "added": time.time()})
    else:
      data.pop(key, None)
    try:
      BOOKMARKS_FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
      pass