import shutil
from collections import namedtuple
from send2trash import send2trash
from utils import parse_page, page_name

# The one engine that changes a merged folder: take pages out (maybe none),
# put new pages in, shift the rest. Everything is rolled back on failure.

# removed:    [(number, file)] existing pages that are taken out
# renames:    [(file, new path)] existing pages that change number / marker / width
# placements: [(source file, final name)] new pages that are put in the gap
SplicePlan = namedtuple(
    "SplicePlan",
    "start end removed renames placements delta width final_last repad",
)

STAGING_NAME = ".splice_staging"

def build_splice_plan(info, start, end, new_pages, chapter_shift):
  """Remove pages start-end (none when end < start), put new_pages at start,
  and shift everything after by the difference.

  new_pages is [(file, chapter number or None)].
  chapter_shift is added to the chapter number of every marker after the gap.
  """
  new_count = len(new_pages)
  delta = new_count - (end - start + 1)
  final_last = max(info.last_number + delta, start + new_count - 1)
  width = max(3, info.existing_width, len(str(final_last)))
  repad = width > info.existing_width

  removed, renames = [], []
  for number, file in info.existing:
    if start <= number <= end:
      removed.append((number, file))
      continue
    chapter = parse_page(file)[1]
    if number > end:
      number += delta
      if chapter:
        chapter += chapter_shift
    target = file.with_name(page_name(number, width, file.suffix, chapter))
    if target != file:
      renames.append((file, target))

  placements = [
      (file, page_name(start + i, width, file.suffix, chapter))
      for i, (file, chapter) in enumerate(new_pages)
  ]
  return SplicePlan(
      start, end, removed, renames, placements, delta, width, final_last, repad
  )

def apply_splice(merged_folder, plan, progress=None):
  """Do the change. On any failure (or Ctrl+C) everything is rolled back.

  Returns the folder holding the removed pages (not recycled yet), or None
  when no page was removed.
  """
  staging = merged_folder / STAGING_NAME
  old_dir = merged_folder / f".replaced_pages_{plan.start}-{plan.end}"
  if staging.exists() or old_dir.exists():
    raise FileExistsError(
        f"Leftover folder from an earlier run: {staging.name} / {old_dir.name}"
    )

  moves = []  # every rename done so far, for rollback

  def move(source, target):
    source.rename(target)
    moves.append((source, target))

  try:
    # 1. Copy the new pages aside under their final names.
    staging.mkdir()
    total = len(plan.placements)
    for i, (file, name) in enumerate(plan.placements, start=1):
      shutil.copy2(file, staging / name)
      if progress:
        progress(i, total)

    # 2. Move the pages that are replaced out of the way.
    if plan.removed:
      old_dir.mkdir()
      for _number, file in plan.removed:
        move(file, old_dir / file.name)

    # 3. Rename the other pages in two steps so names never collide.
    temps = []
    for i, (file, target) in enumerate(plan.renames):
      temp = merged_folder / f".__tmp_{i}{file.suffix}"
      move(file, temp)
      temps.append((temp, target))
    for temp, target in temps:
      if target.exists():
        raise FileExistsError(f"{target.name} already exists")
      move(temp, target)

    # 4. Put the new pages into the gap.
    for _file, name in plan.placements:
      target = merged_folder / name
      if target.exists():
        raise FileExistsError(f"{name} already exists")
      move(staging / name, target)

    staging.rmdir()
    return old_dir if plan.removed else None

  except BaseException:
    for source, target in reversed(moves):
      try:
        target.rename(source)
      except OSError:
        pass
    shutil.rmtree(staging, ignore_errors=True)
    try:
      old_dir.rmdir()
    except OSError:
      pass
    raise

def recycle(folder):
  """Send a folder to the recycle bin; returns an error or None."""
  try:
    send2trash(str(folder))
    return None
  except Exception as exc:
    return exc