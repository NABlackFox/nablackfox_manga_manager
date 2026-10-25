import hashlib
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from functions.convert_thumbnail import find_first_image
from utils import list_images, list_subfolders, parse_page

try:
  from PIL import Image, ImageOps
except ImportError:
  Image = None

# Local web library + reader. Every page is a normal link, so you can middle-click
# several manga into separate tabs: each tab is independent and keeps its own place.

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_FOLDER = PROJECT_ROOT / "local_web"
PROGRESS_FILE = PROJECT_ROOT / "reader_progress.json"
CACHE_FOLDER = PROJECT_ROOT / ".reader_cache"
THUMB_WIDTH = 360

_progress_lock = threading.Lock()
_scan_lock = threading.Lock()
_scan_cache = {}


# ---------- library lookups (names always come from real folders, never from raw paths) ----------

def find_author(manga_root, name):
  return next((f for f in list_subfolders(manga_root) if f.name == name), None)


def find_manga(manga_root, author, name):
  author_folder = find_author(manga_root, author or "")
  if author_folder is None:
    return None
  return next((f for f in list_subfolders(author_folder) if f.name == name), None)


def author_thumb_source(author_folder):
  """The one image that sits directly in an author folder."""
  images = list_images(author_folder)
  return images[0] if images else None


def manga_thumb_source(manga_folder):
  first = find_first_image(manga_folder)
  if isinstance(first, Path):
    return first
  images = list_images(manga_folder)
  return images[0] if images else None


def make_thumb(source):
  """Small cached JPEG of an image, so the grids load fast. Returns bytes."""
  stat = source.stat()
  key = hashlib.sha1(f"{source.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{THUMB_WIDTH}".encode()).hexdigest()
  cached = CACHE_FOLDER / f"{key}.jpg"
  try:
    return cached.read_bytes()
  except OSError:
    pass

  if Image is None:
    return source.read_bytes()
  with Image.open(source) as image:
    image = ImageOps.exif_transpose(image)
    try:
      image.seek(0)
    except EOFError:
      pass
    image = image.convert("RGB")
    image.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 2))
    CACHE_FOLDER.mkdir(exist_ok=True)
    temp = cached.with_suffix(".tmp")
    image.save(temp, format="JPEG", quality=82)
    temp.replace(cached)
  return cached.read_bytes()


# ---------- reading position ----------

def _read_progress():
  try:
    return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
  except (OSError, ValueError):
    return {}


def load_progress(folder):
  return _read_progress().get(str(folder.resolve()), {})


def save_progress(folder, index, fraction):
  with _progress_lock:
    data = _read_progress()
    data[str(folder.resolve())] = {"index": index, "fraction": fraction}
    try:
      PROGRESS_FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    except OSError:
      pass


# ---------- pages of one manga ----------

def scan_pages(folder):
  """Every image in reading order with its chapter marker and size (cached per folder state)."""
  images = list_images(folder)
  signature = tuple((f.name, f.stat().st_mtime_ns) for f in images)
  with _scan_lock:
    cached = _scan_cache.get(folder)
    if cached and cached[0] == signature:
      return cached[1]

  pages = []
  for file in images:
    parsed = parse_page(file)
    width = height = None
    if Image is not None:
      try:
        with Image.open(file) as image:
          width, height = image.size
      except Exception:
        pass
    pages.append({"file": file, "chapter": parsed[1] if parsed else None, "w": width, "h": height})

  with _scan_lock:
    _scan_cache[folder] = (signature, pages)
  return pages


# ---------- server ----------

def make_handler(manga_root):
  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
      pass  # keep the terminal clean

    def _send(self, status, body, content_type, cache="no-cache"):
      self.send_response(status)
      self.send_header("Content-Type", content_type)
      self.send_header("Content-Length", str(len(body)))
      if cache:
        self.send_header("Cache-Control", cache)
      self.end_headers()
      self.wfile.write(body)

    def _json(self, payload):
      self._send(200, json.dumps(payload).encode(), "application/json")

    def _html(self, name):
      self._send(200, (WEB_FOLDER / name).read_bytes(), "text/html; charset=utf-8")

    def _not_found(self):
      self._send(404, b"Not found", "text/plain")

    def do_GET(self):
      url = urlparse(self.path)
      query = {k: v[0] for k, v in parse_qs(url.query).items()}
      author, manga = query.get("a"), query.get("m")
      try:
        if url.path == "/":
          self._html("library.html")
        elif url.path == "/author":
          self._html("library.html")
        elif url.path == "/read":
          self._html("index.html")
        elif url.path == "/api/library":
          self._json(self._library())
        elif url.path == "/api/author":
          self._json(self._author(author))
        elif url.path == "/api/manga":
          self._json(self._manga(author, manga))
        elif url.path == "/thumb":
          self._thumb(author, manga)
        elif url.path == "/img":
          self._image(author, manga, query.get("i", ""))
        else:
          self._not_found()
      except ConnectionError:
        pass  # the browser closed or reloaded the page mid-request: nothing to do
      except (LookupError, ValueError, OSError):
        try:
          self._not_found()
        except ConnectionError:
          pass

    def do_POST(self):
      url = urlparse(self.path)
      query = {k: v[0] for k, v in parse_qs(url.query).items()}
      if url.path != "/api/progress":
        return self._not_found()
      try:
        folder = self._require_manga(query.get("a"), query.get("m"))
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length))
        count = len(scan_pages(folder))
        index = max(0, min(int(data["index"]), count - 1))
        fraction = max(0.0, min(float(data["fraction"]), 1.0))
        save_progress(folder, index, fraction)
        self._send(204, b"", "text/plain", cache=None)
      except LookupError:
        self._not_found()
      except (ValueError, KeyError, TypeError):
        self._send(400, b"Bad request", "text/plain")

    # ----- data -----

    def _require_manga(self, author, manga):
      folder = find_manga(manga_root, author, manga)
      if folder is None:
        raise LookupError
      return folder

    def _library(self):
      authors = []
      for folder in sorted(list_subfolders(manga_root), key=lambda f: f.name.casefold()):
        authors.append({
            "name": folder.name,
            "count": len(list_subfolders(folder)),
            "thumb": author_thumb_source(folder) is not None,
        })
      return authors

    def _author(self, author):
      folder = find_author(manga_root, author or "")
      if folder is None:
        raise LookupError
      progress = _read_progress()
      manga = []
      for item in list_subfolders(folder):
        images = list_images(item)
        if not images:
          continue
        saved = progress.get(str(item.resolve()), {})
        manga.append({
            "name": item.name,
            "pages": len(images),
            "read": saved.get("index") + 1 if "index" in saved else 0,
        })
      return {"name": folder.name, "manga": manga}

    def _manga(self, author, manga):
      folder = self._require_manga(author, manga)
      pages = scan_pages(folder)
      return {
          "author": author,
          "title": folder.name,
          "pages": [{"chapter": p["chapter"], "w": p["w"], "h": p["h"]} for p in pages],
          "progress": load_progress(folder),
      }

    def _thumb(self, author, manga):
      if manga:
        source = manga_thumb_source(self._require_manga(author, manga))
      else:
        folder = find_author(manga_root, author or "")
        if folder is None:
          raise LookupError
        source = author_thumb_source(folder)
      if source is None:
        raise LookupError
      self._send(200, make_thumb(source), "image/jpeg", "max-age=3600")

    def _image(self, author, manga, index):
      files = [p["file"] for p in scan_pages(self._require_manga(author, manga))]
      file = files[int(index)] if 0 <= int(index) < len(files) else None
      if file is None:
        raise LookupError
      content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
      self._send(200, file.read_bytes(), content_type, "max-age=3600")

  return Handler


def start_reader(manga_root):
  """Start the library on a free local port. Returns (server, url)."""
  # 127.0.0.1 only: nothing outside this computer can reach it.
  server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Path(manga_root)))
  server.daemon_threads = True
  threading.Thread(target=server.serve_forever, daemon=True).start()
  return server, f"http://127.0.0.1:{server.server_address[1]}/"