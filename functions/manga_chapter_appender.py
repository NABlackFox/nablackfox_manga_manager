from collections import namedtuple
import re
import shutil
from utils import list_images, parse_page, page_name

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

def numbering(info, new_page_count):
  """Work out how the new pages will be numbered."""
  first_new = info.last_number + 1
  final_number = info.last_number + new_page_count
  width = max(3, info.existing_width, len(str(final_number)))
  needs_repad = bool(info.existing) and width > info.existing_width
  return first_new, final_number, width, needs_repad

def build_updated_folder(merged_folder, added_chapters):
  """Return merged folder path with updated chapter range count."""
  match = re.search(r"^(.*Chapters\s+1-)(\d+)\s*$", merged_folder.name)
  if not match:
    return None

  prefix, count = match.groups()
  return merged_folder.with_name(f"{prefix}{int(count) + added_chapters}")

def repad_existing(info, width):
  """Rename existing numbered pages to match new digit width."""
  done = []
  try:
    for number, file in info.existing:
      chapter = parse_page(file)[1]
      target = file.with_name(page_name(number, width, file.suffix, chapter))
      file.rename(target)
      done.append((target, file))
  except BaseException:
    for target, original in reversed(done):
      try:
        target.rename(original)
      except OSError:
        pass
    raise

def chapter_count(merged_folder, info):
  """How many chapters the merged folder holds so far."""
  match = re.search(r"Chapters\s+1-(\d+)\s*$", merged_folder.name)
  if match:
    return int(match.group(1))
  chapters = [parse_page(f)[1] for _, f in info.existing]
  return max((c for c in chapters if c), default=0)

def copy_pages(plan, merged_folder, first_new, width, first_chapter):
  """Copy new pages into the merged folder continuing from first_new.

  The first page of every new chapter is named like 031-chapter3.png.
  """
  chapter = first_chapter - 1
  last_label = None
  for number, (file, label) in enumerate(plan, start=first_new):
    marker = None
    if label != last_label:
      chapter += 1
      marker = chapter
      last_label = label
    shutil.copy2(file, merged_folder / page_name(number, width, file.suffix, marker))
    yield number - first_new + 1, len(plan)