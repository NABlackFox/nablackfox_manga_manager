from pathlib import Path
import re
import shutil

from send2trash import send2trash  # pip install send2trash

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

def natural_key(path):
  """Sort key that orders names by the numbers inside them (2 before 10)."""
  return [
      int(part) if part.isdigit() else part.lower()
      for part in re.split(r"(\d+)", path.name)
  ]

def list_subfolders(folder):
  """Return the sub folders of a folder (hidden ones skipped), in window order."""
  folders = [
      f for f in folder.iterdir() if f.is_dir() and not f.name.startswith(".")
  ]
  folders.sort(key=natural_key)
  return folders

def list_images(folder):
  """Return the image files in a folder, sorted by the number in the name."""
  images = [
      f
      for f in folder.iterdir()
      if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
  ]
  images.sort(key=natural_key)
  return images

def is_inside(child, parent):
  """True if child is the same as parent or located somewhere inside it."""
  child, parent = child.resolve(), parent.resolve()
  return child == parent or parent in child.parents

def build_merged_name(first_name, chapter_count):
  """Build the output folder name from the first chapter's folder name.

  'nhentai-655935 - [Author] Title [English] [Tag] ['
    -> '[Author] 655935 Title Chapters 1-N'
  'nhentai-225475 - (C93) [Author] Title [English] {site.com}'
    -> '[Author] 225475 Title Chapters 1-N'
  Anything before the author [..] (like the event "(C93)") and everything
  after the title (tags in [] or {}) is dropped.
  Returns None if the name does not follow the nhentai pattern.
  """
  match = re.match(
      r"^nhentai-(\d+)\s*-\s*[^\[]*(\[[^\]]*\])\s*(.*)$", first_name
  )
  if not match:
    return None

  code, author, rest = match.groups()
  # Everything from the next "[" or "{" onward is tags, so cut it off
  rest = re.split(r"[\[{]", rest, maxsplit=1)[0]
  rest = re.sub(r"\s+", " ", rest).strip()

  name = " ".join(part for part in (author, code, rest) if part)
  name = re.sub(r'[<>:"/\\|?*]', "", name)  # characters Windows does not allow
  chapters = f"Chapters 1-{chapter_count}"
  return f"{name} {chapters}".rstrip(". ")

def build_plan(folders):
  """List every page to copy as (source file, folder name), folder by folder."""
  plan = []
  for folder in folders:
    plan.extend((img, folder.name) for img in list_images(folder))
  return plan

def copy_pages(plan, output_folder):
  """Copy the pages into output_folder, numbered continuously from 1.

  Zero-padding grows automatically (at least 3 digits). Yields
  (pages copied so far, total pages) after every page.
  """
  width = max(3, len(str(len(plan))))
  output_folder.mkdir(parents=True, exist_ok=True)
  for number, (file, _label) in enumerate(plan, start=1):
    shutil.copy2(file, output_folder / f"{number:0{width}d}{file.suffix}")
    yield number, len(plan)

def recycle_folders(folders):
  """Send each folder to the recycle bin (it can be restored from there).

  Yields (folder, error) after every folder; error is None on success.
  """
  for folder in folders:
    try:
      send2trash(str(folder))
      error = None
    except Exception as exc:
      error = exc
    yield folder, error