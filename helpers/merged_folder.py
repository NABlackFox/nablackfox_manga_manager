import re
from collections import namedtuple
from utils import list_images, parse_page

# Read-only helpers: look at a merged folder, never change it.

MergedInfo = namedtuple(
    "MergedInfo", "all_images existing last_number existing_width ignored"
)

def scan_merged_folder(folder):
  """Read the numbered pages of an already merged folder."""
  all_images = list_images(folder)
  existing = []
  for f in all_images:
    parsed = parse_page(f)
    if parsed:
      existing.append((parsed[0], f))

  if existing:
    last_number = max(number for number, _ in existing)
    existing_width = max(len(re.match(r"\d+", f.stem).group()) for _, f in existing)
  else:
    last_number = 0
    existing_width = 3

  ignored = len(all_images) - len(existing)
  return MergedInfo(all_images, existing, last_number, existing_width, ignored)

def read_pages(folder):
  """Return ({page number: [files]}, {chapter: [(page number, file)]})."""
  pages = {}
  markers = {}
  for file in list_images(folder):
    parsed = parse_page(file)
    if not parsed:
      continue
    number, chapter = parsed
    pages.setdefault(number, []).append(file)
    if chapter:
      markers.setdefault(chapter, []).append((number, file))
  return pages, markers

def merged_chapter_count(folder):
  """Return X for a folder named '... Chapters 1-X', else None."""
  match = re.search(r"Chapters\s+1-(\d+)\s*$", folder.name)
  return int(match.group(1)) if match else None

def list_merged_folders(folders):
  return [f for f in folders if merged_chapter_count(f)]

def chapter_count(merged_folder, info):
  """How many chapters the merged folder holds so far."""
  count = merged_chapter_count(merged_folder)
  if count:
    return count
  chapters = [parse_page(f)[1] for _, f in info.existing]
  return max((c for c in chapters if c), default=0)

def build_updated_folder(merged_folder, added_chapters):
  """Return the folder path with 'Chapters 1-X' raised by added_chapters.

  None when the name has no 'Chapters 1-X' ending or the new name is taken.
  """
  match = re.search(r"^(.*Chapters\s+1-)(\d+)\s*$", merged_folder.name)
  if not match:
    return None
  prefix, count = match.groups()
  new_folder = merged_folder.with_name(f"{prefix}{int(count) + added_chapters}")
  return None if new_folder.exists() else new_folder