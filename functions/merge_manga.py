import re
import shutil
from send2trash import send2trash
from utils import list_images, page_name

def build_merged_name(first_name, chapter_count):
  """Build output folder name from the first chapter's folder name."""
  match = re.match(
      r"^nhentai-(\d+)\s*-\s*[^\[]*(\[[^\]]*\])\s*(.*)$", first_name
  )
  if not match:
    return None

  code, author, rest = match.groups()
  rest = re.split(r"[\[{]", rest, maxsplit=1)[0]
  rest = re.sub(r"\s+", " ", rest).strip()

  name = " ".join(part for part in (author, code, rest) if part)
  name = re.sub(r'[<>:"/\\|?*]', "", name)
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

  The first page of every chapter is named like 001-chapter1.png.
  """
  width = max(3, len(str(len(plan))))
  output_folder.mkdir(parents=True, exist_ok=True)
  chapter = 0
  last_label = None
  for number, (file, label) in enumerate(plan, start=1):
    marker = None
    if label != last_label:
      chapter += 1
      marker = chapter
      last_label = label
    shutil.copy2(file, output_folder / page_name(number, width, file.suffix, marker))
    yield number, len(plan)

def recycle_folders(folders):
  """Send each folder to the recycle bin."""
  for folder in folders:
    try:
      send2trash(str(folder))
      error = None
    except Exception as exc:
      error = exc
    yield folder, error