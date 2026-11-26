"""Remembers where you stopped reading each manga."""
import json
import threading
import time

from config import PROJECT_ROOT

PROGRESS_FILE = PROJECT_ROOT / "reader_progress.json"
_lock = threading.Lock()


def read_all():
  try:
    return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
  except (OSError, ValueError):
    return {}


def load(folder):
  return read_all().get(str(folder.resolve()), {})


def _write(data):
  try:
    PROGRESS_FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
  except OSError:
    pass


def save(folder, index, fraction):
  with _lock:
    data = read_all()
    data[str(folder.resolve())] = {"index": index, "fraction": fraction, "time": time.time()}
    _write(data)


def clear(folder):
  """Forget where you were in one manga (it counts as unread again)."""
  with _lock:
    data = read_all()
    if data.pop(str(folder.resolve()), None) is not None:
      _write(data)


def clear_all():
  with _lock:
    _write({})
