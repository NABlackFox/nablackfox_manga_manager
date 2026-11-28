"""Reads the meta.json that comes with a downloaded manga (the gallery information from nhentai).

The file sits directly in the manga folder, next to the pages:

  {"id": 374818, "title": {"english": "...", "japanese": "..."}, "upload_date": 1632817586,
   "num_pages": 48, "num_favorites": 13509, "scanlator": "",
   "tags": [{"id": 33172, "type": "category", "name": "doujinshi"}, ...]}

The file comes from the internet, so nothing in it is trusted: every value is checked for its type and
cut to a sensible length, and a broken or missing file simply means "no information" (None).
"""
import json
import threading

META_NAME = "meta.json"

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TEXT = 400
MAX_TAG = 120
MAX_TAGS = 300

_lock = threading.Lock()
_cache = {}   # file path -> ((mtime, size), normalised meta or None)


def _text(value, limit=MAX_TEXT):
  return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def _number(value):
  if isinstance(value, bool):
    return None
  if isinstance(value, float) and value.is_integer():
    value = int(value)
  return value if isinstance(value, int) and value >= 0 else None


def _tags(raw):
  tags, seen = [], set()
  for item in raw if isinstance(raw, list) else []:
    if isinstance(item, dict):
      kind, name = _text(item.get("type"), 30).lower() or "tag", _text(item.get("name"), MAX_TAG)
    elif isinstance(item, str):
      kind, name = "tag", _text(item, MAX_TAG)
    else:
      continue
    key = (kind, name.casefold())
    if not name or ":" in kind or key in seen:
      continue
    seen.add(key)
    tags.append({"type": kind, "name": name})
    if len(tags) >= MAX_TAGS:
      break
  return tags


def _normalise(raw):
  if not isinstance(raw, dict):
    return None
  title = raw.get("title")
  if isinstance(title, str):
    title = {"english": title}
  if not isinstance(title, dict):
    title = {}
  english, japanese, pretty = (_text(title.get(key)) for key in ("english", "japanese", "pretty"))

  meta = {
      "id": _number(raw.get("id")),
      "title": english or pretty or japanese,          # the one to show
      "english": english,
      "japanese": japanese,
      "pretty": pretty,
      "uploaded": _number(raw.get("upload_date")),      # unix time, seconds
      "pages": _number(raw.get("num_pages")),
      "favorites": _number(raw.get("num_favorites")),
      "scanlator": _text(raw.get("scanlator"), 100),
      "tags": _tags(raw.get("tags")),
  }
  meta = {key: value for key, value in meta.items() if value not in (None, "", [])}
  return meta if {"id", "title", "tags"} & set(meta) else None


def read(folder):
  """The cleaned-up meta.json of a manga folder, or None when there is none (or it is unusable)."""
  path = folder / META_NAME
  try:
    stat = path.stat()
  except OSError:
    return None
  signature = (stat.st_mtime_ns, stat.st_size)
  with _lock:
    cached = _cache.get(path)
    if cached and cached[0] == signature:
      return cached[1]

  meta = None
  if stat.st_size <= MAX_FILE_BYTES:
    try:
      meta = _normalise(json.loads(path.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError):
      meta = None
  with _lock:
    _cache[path] = (signature, meta)
  return meta


def brief(meta):
  """The short form sent with every manga in a list (the library searches it in the browser).

  Tags become "type:name" strings, which keeps the whole library small enough to cache.
  """
  if not meta:
    return None
  short = {key: meta[key] for key in ("id", "title", "english", "japanese", "pretty", "uploaded", "favorites", "scanlator") if key in meta}
  for key in ("english", "pretty"):         # same as the title: do not send it twice
    if short.get(key) == short.get("title"):
      del short[key]
  short["tags"] = [f"{tag['type']}:{tag['name']}" for tag in meta.get("tags", [])]
  return short
