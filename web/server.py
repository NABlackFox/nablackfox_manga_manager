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

from terminal.shared.utils import list_images, list_subfolders, parse_page
from web.bookmarks import bookmarks
from web.reader import progress
from web.library.library import (
    author_thumb_source, find_author, find_manga, manga_thumb_source, scan_pages,
)
from web.library.thumbs import make_thumb
from web.reader import progress

WEB_FOLDER = Path(__file__).resolve().parent
DOMAINS = ("shared", "library", "reader", "bookmarks")
TEMPLATE_ROOTS = [WEB_FOLDER / d / "templates" for d in DOMAINS]
STATIC_ROOTS = [WEB_FOLDER / d / "static" for d in DOMAINS]


def _chapters(folder):
  """Chapter number of every page (None when it does not start one), read from file names only.

  scan_pages() also opens every image to get its size, which is far too slow to run for each
  bookmark on every page load. Chapters live in the file names, so this just lists the folder.
  """
  return [(parse_page(f) or (None, None))[1] for f in list_images(folder)]


def _first_chapter_index(chapters):
  """Index of the first page that starts a chapter (0 when the manga has no chapter markers)."""
  return next((i for i, chapter in enumerate(chapters) if chapter), 0)


def _bookmark_info(folder, entry):
  """{"page": 1-based page, "chapter": chapter that page belongs to or None} for a bookmark entry."""
  chapters = _chapters(folder)
  index = entry.get("page")
  index = _first_chapter_index(chapters) if not isinstance(index, int) else index  # old whole-manga bookmark
  index = max(0, min(index, len(chapters) - 1))
  chapter = next((c for c in reversed(chapters[:index + 1]) if c), None)
  return {"page": index + 1, "chapter": chapter}


def _find(roots, relative):
  """First domain folder that has this file (and the path stays inside that folder)."""
  for root in roots:
    file = (root / relative).resolve()
    if root.resolve() in file.parents and file.is_file():
      return file
  raise LookupError

# {{> name}} in a template is replaced by templates/partials/name.html
INCLUDE = re.compile(r"\{\{>\s*([\w-]+)\s*\}\}")

# URL path -> template file
PAGES = {
    "/": "library.html",
    "/author": "library.html",
    "/manga": "manga.html",
    "/bookmarks": "bookmarks.html",
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
      html = _find(TEMPLATE_ROOTS, name).read_text(encoding="utf-8")
      html = INCLUDE.sub(
          lambda m: _find(TEMPLATE_ROOTS, f"partials/{m.group(1)}.html").read_text(encoding="utf-8"),
          html,
      )
      self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

    def _static(self, relative):
      file = _find(STATIC_ROOTS, relative)
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
        elif url.path == "/api/bookmarks":
          self._json(self._bookmarks())
        elif url.path == "/api/recent":
          self._json(self._recent())
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
      if url.path not in ("/api/progress", "/api/bookmark"):
        return self._not_found()
      try:
        folder = self._require_manga(query.get("a"), query.get("m"))
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length))
        if url.path == "/api/bookmark":
          if not data["on"]:
            bookmarks.set_marked(folder, folder.parent.name, folder.name, False)
            return self._json(None)
          chapters = _chapters(folder)
          if data.get("index") is None:
            index = _first_chapter_index(chapters)    # bookmarked from the library: first chapter
          else:
            index = max(0, min(int(data["index"]), len(chapters) - 1))
          bookmarks.set_marked(folder, folder.parent.name, folder.name, True, index)
          return self._json(_bookmark_info(folder, {"page": index}))
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
      marked = bookmarks.read_all()
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
            "bookmarked": _bookmark_info(item, marked[str(item.resolve())]) if str(item.resolve()) in marked else None,
        })
      return {"name": folder.name, "manga": manga}

    def _bookmarks(self):
      saved_all = progress.read_all()
      items = []
      for entry in sorted(bookmarks.read_all().values(), key=lambda e: e.get("added", 0), reverse=True):
        folder = find_manga(manga_root, entry.get("author"), entry.get("manga"))
        if folder is None:
          continue  # renamed or deleted since it was bookmarked
        saved = saved_all.get(str(folder.resolve()), {})
        items.append({
            "author": folder.parent.name,
            "name": folder.name,
            "pages": len(list_images(folder)),
            "read": saved.get("index") + 1 if "index" in saved else 0,
            "bookmarked": _bookmark_info(folder, entry),
        })
      return items

    def _recent(self, limit=12):
      """Manga you are in the middle of, most recently read first (finished ones are left out)."""
      marked = bookmarks.read_all()
      entries = sorted(progress.read_all().items(), key=lambda kv: kv[1].get("time", 0), reverse=True)
      items = []
      for key, saved in entries:
        path = Path(key)
        folder = find_manga(manga_root, path.parent.name, path.name)
        if folder is None or "index" not in saved:
          continue  # renamed or deleted since it was read
        pages = len(list_images(folder))
        read = saved["index"] + 1
        if pages == 0 or read >= pages:
          continue  # finished
        mark = marked.get(str(folder.resolve()))
        items.append({
            "author": folder.parent.name,
            "name": folder.name,
            "pages": pages,
            "read": read,
            "bookmarked": _bookmark_info(folder, mark) if mark else None,
        })
        if len(items) >= limit:
          break
      return items

    def _manga(self, author, manga):
      folder = self._require_manga(author, manga)
      pages = scan_pages(folder)
      return {
          "author": author,
          "title": folder.name,
          "pages": [{"chapter": p["chapter"], "w": p["w"], "h": p["h"]} for p in pages],
          "progress": progress.load(folder),
          "bookmarked": (_bookmark_info(folder, entry) if (entry := bookmarks.get(folder)) else None),
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