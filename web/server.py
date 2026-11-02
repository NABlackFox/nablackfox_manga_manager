"""Local web library + reader.

Every page is a normal link, so you can middle-click several manga into separate
tabs: each tab is independent and keeps its own place.
"""
import json
import mimetypes
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from terminal.utils import list_images, list_subfolders
from web import progress
from web.library import (
    author_thumb_source, find_author, find_manga, manga_thumb_source, scan_pages,
)
from web.thumbs import make_thumb

WEB_FOLDER = Path(__file__).resolve().parent
TEMPLATES = WEB_FOLDER / "templates"
STATIC = WEB_FOLDER / "static"

# {{> name}} in a template is replaced by templates/partials/name.html
INCLUDE = re.compile(r"\{\{>\s*([\w-]+)\s*\}\}")

# URL path -> template file
PAGES = {
    "/": "library.html",
    "/author": "library.html",
    "/manga": "manga.html",
    "/read": "reader.html",
}


def make_handler(manga_root):
  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
      pass  # keep the terminal clean

    # ----- responses -----

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

    def _not_found(self):
      self._send(404, b"Not found", "text/plain")

    def _template(self, name):
      html = (TEMPLATES / name).read_text(encoding="utf-8")
      html = INCLUDE.sub(lambda m: (TEMPLATES / "partials" / f"{m.group(1)}.html").read_text(encoding="utf-8"), html)
      self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    def _static(self, relative):
      file = (STATIC / relative).resolve()
      if STATIC.resolve() not in file.parents or not file.is_file():
        raise LookupError
      kind = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
      if kind.startswith("text/") or kind == "application/javascript":
        kind += "; charset=utf-8"
      self._send(200, file.read_bytes(), kind)

    # ----- routing -----

    def do_GET(self):
      url = urlparse(self.path)
      query = {k: v[0] for k, v in parse_qs(url.query).items()}
      author, manga = query.get("a"), query.get("m")
      try:
        if url.path in PAGES:
          self._template(PAGES[url.path])
        elif url.path.startswith("/static/"):
          self._static(url.path[len("/static/"):])
        elif url.path == "/api/library":
          self._json(self._library())
        elif url.path == "/api/author":
          self._json(self._author(author))
        elif url.path == "/api/manga":
          self._json(self._manga(author, manga))
        elif url.path == "/thumb":
          self._thumb(author, manga)
        elif url.path == "/pthumb":
          self._page_thumb(author, manga, query.get("i", ""))
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
        progress.save(folder, index, fraction)
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
      saved_all = progress.read_all()
      manga = []
      for item in list_subfolders(folder):
        images = list_images(item)
        if not images:
          continue
        saved = saved_all.get(str(item.resolve()), {})
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
          "progress": progress.load(folder),
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

    def _page_thumb(self, author, manga, index):
      files = [p["file"] for p in scan_pages(self._require_manga(author, manga))]
      i = int(index)
      if not 0 <= i < len(files):
        raise LookupError
      self._send(200, make_thumb(files[i]), "image/jpeg", "max-age=3600")

    def _image(self, author, manga, index):
      files = [p["file"] for p in scan_pages(self._require_manga(author, manga))]
      i = int(index)
      if not 0 <= i < len(files):
        raise LookupError
      file = files[i]
      kind = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
      self._send(200, file.read_bytes(), kind, "max-age=3600")

  return Handler


def start_server(manga_root, port=0):
  """Start the library on a local port (0 = any free one). Returns (server, url)."""
  # 127.0.0.1 only: nothing outside this computer can reach it.
  server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(Path(manga_root)))
  server.daemon_threads = True
  threading.Thread(target=server.serve_forever, daemon=True).start()
  return server, f"http://127.0.0.1:{server.server_address[1]}/"
