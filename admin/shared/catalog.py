"""What the downloader has seen: gallery titles (for naming files) and cover addresses (for thumbnails).

Shared by search (writes it) and downloads (reads the title), so the two modules never import each other.
"""
import threading
from collections import OrderedDict

_LIMIT = 2000
_lock = threading.Lock()
_items = OrderedDict()   # gallery id -> {"title": str, "thumb": str, "pages": int}


def remember(gallery_id, **fields):
  with _lock:
    _items.setdefault(gallery_id, {}).update(fields)
    _items.move_to_end(gallery_id)
    while len(_items) > _LIMIT:
      _items.popitem(last=False)


def get(gallery_id):
  with _lock:
    return dict(_items.get(gallery_id, {}))
