"""Local downloader: search an author, pick manga, download their zips into the zip source folder.

A separate server from the reader, on its own port, so the API key never goes near the reading pages.
Modules (each has its own templates / static folder): shared, search, downloads.
"""
import json
import mimetypes
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import config
from admin.downloads.downloads import DownloadQueue
from admin.search import search
from admin.shared.nhentai_client import ApiError, Client

ADMIN_FOLDER = Path(__file__).resolve().parent
DOMAINS = ("shared", "search", "downloads")
TEMPLATE_ROOTS = [ADMIN_FOLDER / d / "templates" for d in DOMAINS]
# base.css / library.css come from the reader so both sites look the same
STATIC_ROOTS = [ADMIN_FOLDER / d / "static" for d in DOMAINS] + [ADMIN_FOLDER.parent / "web" / "shared" / "static"]
INCLUDE = re.compile(r"\{\{>\s*([\w-]+)\s*\}\}")
MAX_BODY = 64 * 1024


def _find(roots, relative):
  for root in roots:
    file = (root / relative).resolve()
    if root.resolve() in file.parents and file.is_file():
      return file
  raise LookupError


def make_handler(client, queue):
  class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
      pass

    # ----- responses -----

    def _send(self, status, body, content_type, cache="no-store"):
      self.send_response(status)
      self.send_header("Content-Type", content_type)
      self.send_header("Content-Length", str(len(body)))
      if cache:
        self.send_header("Cache-Control", cache)
      self.end_headers()
      self.wfile.write(body)

    def _json(self, payload, status=200):
      self._send(status, json.dumps(payload).encode(), "application/json")

    def _error(self, message, status=400):
      self._json({"error": message}, status)

    # ----- safety: only this computer's own page may talk to us -----

    def _allowed(self):
      port = self.server.server_address[1]
      if self.headers.get("Host") not in (f"127.0.0.1:{port}", f"localhost:{port}"):
        return False    # blocks DNS-rebinding tricks
      origin = self.headers.get("Origin")
      return origin is None or origin in (f"http://127.0.0.1:{port}", f"http://localhost:{port}")

    # ----- routing -----

    def do_GET(self):
      if not self._allowed():
        return self._error("Forbidden", 403)
      url = urlparse(self.path)
      query = {k: v[0] for k, v in parse_qs(url.query).items()}
      try:
        if url.path == "/":
          html = _find(TEMPLATE_ROOTS, "admin.html").read_text(encoding="utf-8")
          html = INCLUDE.sub(lambda m: _find(TEMPLATE_ROOTS, f"partials/{m.group(1)}.html").read_text(encoding="utf-8"), html)
          self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif url.path.startswith("/static/"):
          file = _find(STATIC_ROOTS, url.path[len("/static/"):])
          kind = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
          if kind.startswith("text/") or kind == "application/javascript":
            kind += "; charset=utf-8"
          self._send(200, file.read_bytes(), kind, cache="no-cache")
        elif url.path == "/api/status":
          self._json({"has_key": client.has_key, "folder": str(queue.folder), "hide": config.NHENTAI_HIDE_TAGS})
        elif url.path == "/api/search":
          self._json(search.search_author(
              client, query.get("q", ""), query.get("page", 1), query.get("hide", ""),
              query.get("account", "1") == "1", query.get("mode", "artist")))
        elif url.path.startswith("/api/thumb/"):
          data, kind = search.thumbnail(client, int(url.path.rsplit("/", 1)[1]))
          self._send(200, data, kind, cache="private, max-age=3600")
        elif url.path == "/api/downloads":
          self._json(queue.snapshot())
        else:
          self._send(404, b"Not found", "text/plain")
      except ApiError as error:
        self._error(str(error), error.status if error.status in (401, 403, 404, 429) else 502)
      except (LookupError, ValueError):
        self._send(404, b"Not found", "text/plain")

    def do_POST(self):
      if not self._allowed():
        return self._error("Forbidden", 403)
      if not self.headers.get("Content-Type", "").startswith("application/json"):
        return self._error("Expected JSON", 415)   # a plain HTML form from another site cannot send this
      try:
        length = int(self.headers.get("Content-Length", 0))
        if not 0 <= length <= MAX_BODY:
          return self._error("Too large", 413)
        data = json.loads(self.rfile.read(length) or b"{}")
        path = urlparse(self.path).path
        if path == "/api/downloads":
          ids = [int(i) for i in data["ids"]][:200]
          if not client.has_key:
            return self._error("No API key. Add NHENTAI_API_KEY=... to the .env file and restart.", 401)
          self._json({"added": queue.enqueue(ids)})
        elif path == "/api/downloads/retry":
          queue.retry(int(data["id"]))
          self._json({})
        elif path == "/api/downloads/cancel":
          queue.cancel_queued()
          self._json({})
        elif path == "/api/downloads/clear":
          queue.clear_finished()
          self._json({})
        else:
          self._send(404, b"Not found", "text/plain")
      except (ValueError, KeyError, TypeError):
        self._error("Bad request", 400)

  return Handler


def start_server(port=0, client=None, queue=None):
  """Start the downloader on a local port (0 = any free one). Returns (server, url)."""
  client = client or Client(config.NHENTAI_API_BASE, config.NHENTAI_API_KEY, config.NHENTAI_USER_AGENT,
                            config.NHENTAI_LIMITS_PER_MINUTE)
  queue = queue or DownloadQueue(client, config.ZIP_SOURCE_FOLDER)
  server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(client, queue))
  server.daemon_threads = True
  server.queue = queue
  threading.Thread(target=server.serve_forever, daemon=True).start()
  return server, f"http://127.0.0.1:{server.server_address[1]}/"
