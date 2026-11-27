"""Search a manga author on the site and list what they made.

Public functions (the only things other modules should call):
  search_author(client, text, page, hide, hide_account_blacklist, mode) -> dict for the page
  thumbnail(client, gallery_id) -> (bytes, content type)
"""
import re
import threading
import time
import urllib.error
import urllib.request

import config
from admin.shared import catalog
from admin.shared.library_ids import owned_ids
from admin.shared.nhentai_client import ApiError

CDN_CACHE_SECONDS = 3600
_cdn = {"time": 0.0, "thumb_servers": []}
_cdn_lock = threading.Lock()
_thumb_cache = {}          # gallery id -> (bytes, content type); small, in memory
_THUMB_CACHE_LIMIT = 400


# ---------- the tag filter ----------

def parse_hide(text):
  """'tag one, 12345, "tag two"' -> (names, ids). Names go into the search; ids are matched on the results."""
  names, ids = [], set()
  for token in re.split(r"[,\n]+", text or ""):
    token = token.strip().strip('"').strip()
    if not token:
      continue
    if token.isdigit():
      ids.add(int(token))
    else:
      names.append(token.replace('"', ""))
  return names, ids


def build_query(text, mode, hide_names):
  """The search string sent to the API.

  mode "artist": artist:"name"      mode "text": the words as typed (also finds circle/group names in titles)
  Every hidden tag name is added as -tag:"name".
  """
  text = text.replace('"', " ").strip()
  parts = [f'artist:"{text}"' if mode == "artist" else f'"{text}"']
  parts += [f'-tag:"{name}"' for name in hide_names]
  return " ".join(parts)


# ---------- reading the answer ----------

def _first(data, *keys):
  for key in keys:
    if isinstance(data, dict) and key in data:
      return data[key]
  return None


def extract_page(payload):
  """(list of galleries, number of pages or None) from a paginated answer, whatever the list is called."""
  if isinstance(payload, list):
    return payload, None
  items = _first(payload, "result", "results", "galleries", "items", "data")
  if not isinstance(items, list):
    keys = ", ".join(sorted(payload)) if isinstance(payload, dict) else type(payload).__name__
    raise ApiError(f"Unexpected search answer (fields: {keys}). The list of galleries was not found.")
  pages = _first(payload, "num_pages", "total_pages", "pages")
  return items, pages if isinstance(pages, int) else None


def _title(item):
  for key in ("english_title", "japanese_title", "title"):
    value = item.get(key)
    if isinstance(value, str) and value.strip():
      return value.strip()
    if isinstance(value, dict):                       # a title object: take its first readable text
      for text in value.values():
        if isinstance(text, str) and text.strip():
          return text.strip()
  return f"#{item.get('id')}"


# ---------- covers ----------

def _server_base(server):
  if isinstance(server, dict):
    server = _first(server, "url", "base_url", "host", "domain") or ""
  server = str(server).strip().rstrip("/")
  if server.startswith("//"):
    server = "https:" + server
  elif server and "://" not in server:
    server = "https://" + server
  return server


def _thumb_servers(client):
  with _cdn_lock:
    if time.time() - _cdn["time"] < CDN_CACHE_SECONDS and _cdn["thumb_servers"]:
      return _cdn["thumb_servers"]
  data = client.request("GET", "/cdn", group="cdn")
  servers = _first(data, "thumb_servers", "thumbnail_servers")
  if servers is None and isinstance(data, dict):
    servers = _first(data.get("cdn") or {}, "thumb_servers")
  bases = [b for b in (_server_base(s) for s in (servers or [])) if b]
  with _cdn_lock:
    _cdn.update(time=time.time(), thumb_servers=bases)
  return bases


def _thumb_url(client, path):
  if not path:
    return None
  if "://" in path or path.startswith("//"):
    return _server_base(path)
  servers = _thumb_servers(client)
  return f"{servers[0]}/{path.lstrip('/')}" if servers else None


def thumbnail(client, gallery_id):
  """Cover image bytes for a gallery found by a search (so the browser never fetches arbitrary addresses)."""
  if gallery_id in _thumb_cache:
    return _thumb_cache[gallery_id]
  path = catalog.get(gallery_id).get("thumb")
  url = _thumb_url(client, path) if path else None
  if not url:
    raise LookupError
  request = urllib.request.Request(url, headers={"User-Agent": client.user_agent})
  try:
    with urllib.request.urlopen(request, timeout=20) as response:   # no API key: it goes to the API only
      data, kind = response.read(), response.headers.get("Content-Type", "image/jpeg")
  except (urllib.error.URLError, OSError):
    raise LookupError from None
  if len(_thumb_cache) >= _THUMB_CACHE_LIMIT:
    _thumb_cache.pop(next(iter(_thumb_cache)))
  _thumb_cache[gallery_id] = (data, kind)
  return data, kind


# ---------- the search ----------

def search_author(client, text, page=1, hide="", hide_account_blacklist=True, mode="artist"):
  text = (text or "").strip()
  if not text:
    raise ApiError("Type an author name first.")
  page = max(1, int(page))

  env_names, env_ids = parse_hide(", ".join(config.NHENTAI_HIDE_TAGS))
  ui_names, ui_ids = parse_hide(hide)
  hide_names = list(dict.fromkeys(env_names + ui_names))
  hide_ids = env_ids | ui_ids

  query = build_query(text, mode if mode in ("artist", "text") else "artist", hide_names)
  payload = client.request("GET", "/search", {"query": query, "sort": "date", "page": page}, group="search")
  galleries, num_pages = extract_page(payload)

  in_library, waiting = owned_ids()
  items, hidden = [], 0
  for gallery in galleries:
    if not isinstance(gallery, dict) or not isinstance(gallery.get("id"), int):
      continue
    if hide_account_blacklist and gallery.get("blacklisted"):
      hidden += 1
      continue
    if hide_ids & set(gallery.get("tag_ids") or []):
      hidden += 1
      continue
    gallery_id = gallery["id"]
    title = _title(gallery)
    catalog.remember(gallery_id, title=title, thumb=gallery.get("thumbnail"), pages=gallery.get("num_pages"))
    items.append({
        "id": gallery_id,
        "title": title,
        "pages": gallery.get("num_pages"),
        "favorites": gallery.get("num_favorites"),
        "have": "library" if gallery_id in in_library else "zip" if gallery_id in waiting else None,
        "thumb": f"/api/thumb/{gallery_id}" if gallery.get("thumbnail") else None,
    })
  return {"items": items, "page": page, "num_pages": num_pages, "hidden": hidden, "query": query,
          "more": bool(galleries) and (num_pages is None or page < num_pages)}
