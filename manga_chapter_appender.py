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

def move_to_recycle_bin(folder):
  """Send a folder to the recycle bin (it can be restored from there)."""
  send2trash(str(folder))

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

def ask_for_merged_folder():
  """Ask for the folder that already contains the merged pages.

  New pages will be appended into this same folder.
  """
  while True:
    text = clean_path(input("Enter the already merged folder: "))
    if text and Path(text).is_dir():
      return Path(text)
    print("  Not a valid folder, try again.")

def ask_for_new_folders(merged_folder):
  """Ask for the new chapter folders. Press Enter on an empty line to finish."""
  folders = []
  print("\nEnter the new chapter folders in the order they should be added.")
  print("Press Enter on an empty line when you are done.\n")

  while True:
    text = clean_path(input(f"New folder {len(folders) + 1}: "))
    if not text:
      if not folders:
        print("You need to enter at least one folder.")
        continue
      break

    folder = Path(text)
    if not folder.exists() or not folder.is_dir():
      print("  Not a valid folder, try again.")
      continue

    # The merged folder must not be a new folder, nor sit inside one, nor
    # contain one (sending a new folder to the recycle bin would take the
    # merged folder along, or the merged folder would be copied into itself)
    if is_inside(folder, merged_folder) or is_inside(merged_folder, folder):
      print("  That folder overlaps with the merged folder, skipping.")
      continue

    if folder.resolve() in [f.resolve() for f in folders]:
      print("  You already added that folder, skipping.")
      continue

    folders.append(folder)

  return folders

def manga_chapter_appender():
  # 1. Read the existing merged folder (this is also the output folder)
  merged_folder = ask_for_merged_folder()

  all_images = list_images(merged_folder)
  existing = [(int(f.stem), f) for f in all_images if f.stem.isdigit()]
  ignored = len(all_images) - len(existing)

  if existing:
    last_number = max(number for number, _ in existing)
    existing_width = max(len(f.stem) for _, f in existing)
    print(
        f"Merged folder has {len(existing)} numbered pages"
        f" (last page: {last_number})."
    )
  else:
    last_number = 0
    existing_width = 3
    print("No numbered pages found in the merged folder. Starting from 1.")

  if ignored:
    print(f"Note: {ignored} image(s) with non-numeric names were ignored.")

  # 2. Get the new chapter folders (added in the order entered)
  folders = ask_for_new_folders(merged_folder)

  # 3. Collect all new images, folder by folder
  plan = []  # list of (source file, folder label)
  for folder in folders:
    images = list_images(folder)
    print(f"{folder.name}: found {len(images)} images")
    plan.extend((img, folder.name) for img in images)

  if not plan:
    print("No image files found in the new folders.")
    return

  first_new = last_number + 1
  final_number = last_number + len(plan)

  # Zero-padding grows automatically (at least 3 digits, never smaller than
  # what the merged folder already uses)
  width = max(3, existing_width, len(str(final_number)))
  needs_repad = bool(existing) and width > existing_width

  print(
      f"\nTotal: {len(plan)} new images will be added as"
      f" {first_new:0{width}d} to {final_number:0{width}d}"
      f" in:\n{merged_folder}"
  )
  print(
      f"After appending, the {len(folders)} new chapter folder(s) will be"
      " moved to the recycle bin."
  )

  # The folder name holds the chapter range, so it has to grow as well
  renamed_folder = build_updated_folder(merged_folder, len(folders))
  if renamed_folder is None:
    print(
        "Note: the merged folder name does not end with 'Chapters 1-N',"
        " so it will not be renamed."
    )
  elif renamed_folder.exists():
    print(
        f"Note: {renamed_folder.name} already exists, so the merged folder"
        " will not be renamed."
    )
    renamed_folder = None
  else:
    print(f"The merged folder will be renamed to:\n{renamed_folder.name}")

  if needs_repad:
    print(
        f"\nThe page count now needs {width} digits, so the {len(existing)}"
        f" existing pages will be renamed to {width} digits"
        " (for example 999 -> 0999) to keep the order correct."
    )

  answer = input("Continue? (y/n): ").strip().lower()
  if answer != "y":
    print("Cancelled. Nothing was changed.")
    return

  # 4. Re-pad existing file names only if the digit width has to grow
  if needs_repad:
    for number, file in existing:
      new_name = f"{number:0{width}d}{file.suffix}"
      file.rename(file.with_name(new_name))

  # 5. Copy the new pages, continuing from the last page number
  print()
  for number, (file, label) in enumerate(plan, start=first_new):
    new_name = f"{number:0{width}d}{file.suffix}"
    shutil.copy2(file, merged_folder / new_name)
    print(f"Copied: [{label}] {file.name} -> {new_name}")

  # 6. Only after every page was copied, send the new folders to the bin
  expected = len(all_images) + len(plan)
  copied = len(list_images(merged_folder))
  if copied < expected:
    print(
        f"\nWarning: expected at least {expected} images in the merged folder"
        f" but found {copied}. The new chapter folders were NOT touched."
    )
    return

  # 7. Update the chapter range in the merged folder's name
  if renamed_folder is not None:
    try:
      merged_folder.rename(renamed_folder)
      print(f"\nRenamed merged folder -> {renamed_folder.name}")
    except Exception as error:
      print(f"\nCould not rename the merged folder ({error})")

  print()
  for folder in folders:
    try:
      move_to_recycle_bin(folder)
      print(f"Recycle bin: {folder}")
    except Exception as error:
      print(f"Could not recycle {folder} ({error})")

  print(
      "\nProcessing completed successfully! The new chapter folders are in"
      " the recycle bin if you need them back."
  )

if __name__ == "__main__":
  manga_chapter_appender()