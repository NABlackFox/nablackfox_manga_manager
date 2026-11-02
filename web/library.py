"""Library lookups. Names always come from real folders, never from raw request paths."""
import threading
from pathlib import Path

from terminal.functions.convert_to_webp import find_first_image
from terminal.utils import list_images, list_subfolders, parse_page

try:
  from PIL import Image
except ImportError:
  Image = None

_scan_lock = threading.Lock()
_scan_cache = {}


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
