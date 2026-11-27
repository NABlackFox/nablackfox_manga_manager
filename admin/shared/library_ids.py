"""Which galleries you already have, found from file and folder names (they contain the nhentai id)."""
import os
import re
import json

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

def _id_from_meta(manga_folder):
  """Read the nhentai gallery ID from a manga folder's meta.json."""
  meta_path = os.path.join(manga_folder, "meta.json")

  try:
    with open(meta_path, "r", encoding="utf-8") as file:
      data = json.load(file)
  except (OSError, json.JSONDecodeError):
    return None

  if not isinstance(data, dict):
    return None

  gallery_id = data.get("id")

  if isinstance(gallery_id, int) and not isinstance(gallery_id, bool):
    return gallery_id

  return None

def owned_ids(manga_root=None, zip_folder=None):
  """(ids in your library, ids of zips waiting in the zip folder)."""
  manga_root = manga_root or config.MANGA_ROOT
  zip_folder = zip_folder or config.ZIP_SOURCE_FOLDER

  library = set()
  for author, is_dir in _names(manga_root):
    if not is_dir or author.startswith("."):
      continue

    author_path = os.path.join(manga_root, author)

    for name, child_is_dir in _names(author_path):
      if not child_is_dir or name.startswith("."):
        continue

      manga_path = os.path.join(author_path, name)
      gallery_id = _id_from_meta(manga_path)

      if gallery_id is not None:
        library.add(gallery_id)

  waiting = set()
  for name, is_dir in _names(zip_folder):
    if not is_dir and name.lower().endswith(".zip"):
      waiting |= _ids_in(name, False)
  return library, waiting
