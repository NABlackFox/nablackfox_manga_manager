"""Remembers where you stopped reading each manga."""
import json
import threading

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


def save(folder, index, fraction):
  with _lock:
    data = read_all()
    data[str(folder.resolve())] = {"index": index, "fraction": fraction}
    try:
      PROGRESS_FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
      pass
