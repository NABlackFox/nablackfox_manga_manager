from collections import namedtuple
import re
import shutil

import merge_manga  # same folder as this file

# What the already merged folder looks like right now
MergedInfo = namedtuple(
    "MergedInfo", "all_images existing last_number existing_width ignored"
)

def scan_merged_folder(folder):
  """Read the numbered pages (001.jpg, 002.png, ...) of an already merged folder."""
  all_images = merge_manga.list_images(folder)
  existing = [(int(f.stem), f) for f in all_images if f.stem.isdigit()]

  if existing:
    last_number = max(number for number, _ in existing)
    existing_width = max(len(f.stem) for _, f in existing)
  else:
    last_number = 0
    existing_width = 3

  ignored = len(all_images) - len(existing)  # images with non-numeric names
  return MergedInfo(all_images, existing, last_number, existing_width, ignored)

def numbering(info, new_page_count):
  """Work out how the new pages will be numbered.

  Returns (first new number, final number, digit width, needs_repad).
  Zero-padding grows automatically (at least 3 digits, never smaller than what
  the merged folder already uses). needs_repad is True when the existing pages
  have to be renamed to more digits to keep the order correct.
  """
  first_new = info.last_number + 1
  final_number = info.last_number + new_page_count
  width = max(3, info.existing_width, len(str(final_number)))
  needs_repad = bool(info.existing) and width > info.existing_width
  return first_new, final_number, width, needs_repad

def build_updated_folder(merged_folder, added_chapters):
  """Return the merged folder path with its 'Chapters 1-N' count increased.

  '[Author] 655935 Title Chapters 1-5' + 3 new chapters
    -> '[Author] 655935 Title Chapters 1-8'
  Returns None if the folder name does not end with 'Chapters 1-N'.
  """
  match = re.search(r"^(.*Chapters\s+1-)(\d+)\s*$", merged_folder.name)
  if not match:
    return None

  prefix, count = match.groups()
  return merged_folder.with_name(f"{prefix}{int(count) + added_chapters}")

def repad_existing(info, width):
  """Rename the existing numbered pages to `width` digits (999 -> 0999).

  If a rename fails, the pages already renamed are put back before the error
  is raised, so the folder is never left half renamed.
  """
  done = []  # (new path, original path)
  try:
    for number, file in info.existing:
      target = file.with_name(f"{number:0{width}d}{file.suffix}")
      file.rename(target)
      done.append((target, file))
  except BaseException:
    for target, original in reversed(done):
      try:
        target.rename(original)
      except OSError:
        pass
    raise

def copy_pages(plan, merged_folder, first_new, width):
  """Copy the new pages into the merged folder, continuing from first_new.

  Yields (new pages copied so far, total new pages) after every page.
  """
  for number, (file, _label) in enumerate(plan, start=first_new):
    shutil.copy2(file, merged_folder / f"{number:0{width}d}{file.suffix}")
    yield number - first_new + 1, len(plan)