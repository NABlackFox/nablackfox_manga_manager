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

def clean_path(text):
  """Strip whitespace and surrounding quotes from a pasted path."""
  return text.strip().strip('"\'')

def ask_for_parent_folder():
  """Ask for the parent (author) folder that contains the folders to merge."""
  while True:
    text = clean_path(input("Enter the parent folder: "))
    if text and Path(text).is_dir():
      return Path(text)
    print("  Not a valid folder, try again.")

def list_subfolders(parent):
  """Return the folders directly inside the parent, in natural order."""
  folders = [
      f for f in parent.iterdir()
      if f.is_dir() and not f.name.startswith(".")
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

def build_merged_name(first_folder, chapter_count):
  """Build the output folder name from the first folder's name.

  'nhentai-655935 - [Author] Title [English] [Tag] ['
    -> '[Author] 655935 Title Chapters 1-N'
  'nhentai-225475 - (C93) [Author] Title [English] {site.com}'
    -> '[Author] 225475 Title Chapters 1-N'
  Anything before the author [..] (like the event "(C93)") and everything
  after the title (tags in [] or {}) is dropped.
  Returns None if the name does not follow the nhentai pattern.
  """
  match = re.match(
      r"^nhentai-(\d+)\s*-\s*[^\[]*(\[[^\]]*\])\s*(.*)$", first_folder.name
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

def ask_for_output_folder(default_output):
  """Show the default output folder and ask y/n. If no, a path must be typed."""
  print(f"\nThe merged folder will be:\n{default_output}")

  while True:
    answer = input("Use this folder? (y/n): ").strip().lower()
    if answer in ("y", "n"):
      break
    print("  Please type y or n.")

  if answer == "y":
    return default_output

  while True:
    text = clean_path(input("Enter the output folder path: "))
    if text:
      return Path(text)
    print("  You need to enter a path.")

def move_to_recycle_bin(folder):
  """Send a folder to the recycle bin (it can be restored from there)."""
  send2trash(str(folder))

def super_merge_manga():
  # 1. Ask for the parent folder
  parent = ask_for_parent_folder()

  # 2. Take every folder inside it that has images (natural order)
  sources = []
  plan = []  # list of (source file, folder label)
  print()
  for folder in list_subfolders(parent):
    images = list_images(folder)
    if not images:
      print(f"{folder.name}: no images, skipped")
      continue
    print(f"{folder.name}: found {len(images)} images")
    sources.append(folder)
    plan.extend((img, folder.name) for img in images)

  if len(sources) < 2:
    print("\nNeed at least 2 folders with images to merge. Nothing was changed.")
    return

  # 3. Name the result after the first folder
  merged_name = build_merged_name(sources[0], len(sources)) or "merged_output"
  output_folder = ask_for_output_folder(parent / merged_name)

  # Do not let the output folder be (or sit inside) one of the source folders,
  # otherwise sending the sources to the recycle bin would take it along.
  # It also should not be the parent folder itself.
  if any(is_inside(output_folder, f) for f in sources):
    print("Error: The output folder cannot be inside one of the source folders.")
    return
  if output_folder.resolve() == parent.resolve():
    print("Error: The output folder cannot be the parent folder itself.")
    return

  # Zero-padding grows automatically (at least 3 digits)
  width = max(3, len(str(len(plan))))
  print(f"\nTotal: {len(plan)} images from {len(sources)} folders -> {output_folder}")
  print(
      f"After merging, the {len(sources)} source folder(s) will be moved to"
      " the recycle bin."
  )

  # 4. Confirm, since every folder in the parent gets merged
  answer = input("Continue? (y/n): ").strip().lower()
  if answer != "y":
    print("Cancelled. Nothing was changed.")
    return

  # 5. Warn before writing into a folder that already has files
  if output_folder.exists() and any(output_folder.iterdir()):
    answer = input(
        "The output folder is not empty. Files with the same names will be"
        " overwritten. Continue? (y/n): "
    ).strip().lower()
    if answer != "y":
      print("Cancelled. Nothing was copied.")
      return

  output_folder.mkdir(parents=True, exist_ok=True)

  # 6. Copy and rename sequentially, always starting from 1
  print()
  for number, (file, label) in enumerate(plan, start=1):
    new_name = f"{number:0{width}d}{file.suffix}"
    shutil.copy2(file, output_folder / new_name)
    print(f"Copied: [{label}] {file.name} -> {new_name}")

  # 7. Only after every page was copied, send the source folders to the bin
  copied = len(list_images(output_folder))
  if copied < len(plan):
    print(
        f"\nWarning: expected at least {len(plan)} images in the output folder"
        f" but found {copied}. The source folders were NOT touched."
    )
    return

  print()
  for folder in sources:
    try:
      move_to_recycle_bin(folder)
      print(f"Recycle bin: {folder}")
    except Exception as error:
      print(f"Could not recycle {folder} ({error})")

  print(
      "\nProcessing completed successfully! The source folders are in the"
      " recycle bin if you need them back."
  )

if __name__ == "__main__":
  super_merge_manga()