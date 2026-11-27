"""Which galleries you already have, found from file and folder names (they contain the nhentai id)."""
import os
import re

import config

FROM_NAME = re.compile(r"nhentai-(\d+)", re.IGNORECASE)
FROM_MERGED = re.compile(r"\]\s+(\d{1,8})\s")   # merged folders are named "[Author] 325605 Title Chapters 1-3"


def _names(folder):
  try:
    with os.scandir(folder) as entries:
      return [(entry.name, entry.is_dir()) for entry in entries]
  except OSError:
    return []


def _ids_in(name, is_dir):
  found = {int(m) for m in FROM_NAME.findall(name)}
  if is_dir and "Chapters 1-" in name:
    found |= {int(m) for m in FROM_MERGED.findall(name)}
  return found


def owned_ids(manga_root=None, zip_folder=None):
  """(ids in your library, ids of zips waiting in the zip folder)."""
  manga_root = manga_root or config.MANGA_ROOT
  zip_folder = zip_folder or config.ZIP_SOURCE_FOLDER

  library = set()
  for author, is_dir in _names(manga_root):
    if not is_dir or author.startswith("."):
      continue
    for name, child_is_dir in _names(os.path.join(manga_root, author)):
      library |= _ids_in(name, child_is_dir)

  waiting = set()
  for name, is_dir in _names(zip_folder):
    if not is_dir and name.lower().endswith(".zip"):
      waiting |= _ids_in(name, False)
  return library, waiting
