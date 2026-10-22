from pathlib import Path
import re
import shutil

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

def ask_for_folders():
  """Ask for source folders one by one. Press Enter on an empty line to finish."""
  folders = []
  print("Enter the manga folders in the order they should be merged.")
  print("Press Enter on an empty line when you are done.\n")

  while True:
    text = clean_path(input(f"Folder {len(folders) + 1}: "))
    if not text:
      if not folders:
        print("You need to enter at least one folder.")
        continue
      break

    folder = Path(text)
    if not folder.exists() or not folder.is_dir():
      print("  Not a valid folder, try again.")
      continue

    if folder.resolve() in [f.resolve() for f in folders]:
      print("  You already added that folder, skipping.")
      continue

    folders.append(folder)

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

def manga_merger():
  # 1. Get the source folders (merged in the order entered)
  folders = ask_for_folders()

  # 2. Get output folder (or use default next to the first source folder)
  default_output = folders[0].parent / "merged_output"
  out_text = clean_path(
      input(
          f"\nEnter the output folder path\n(Press Enter to use"
          f" [{default_output}]): "
      )
  )
  output_folder = Path(out_text) if out_text else default_output

  # Do not let the output folder be one of the source folders
  if output_folder.resolve() in [f.resolve() for f in folders]:
    print("Error: The output folder cannot be one of the source folders.")
    return

  # 3. Collect all images, folder by folder, then number them continuously
  plan = []  # list of (source file, folder label)
  for folder in folders:
    images = list_images(folder)
    print(f"{folder.name}: found {len(images)} images")
    plan.extend((img, folder.name) for img in images)

  if not plan:
    print("No image files found in the specified folders.")
    return

  # Zero-padding grows automatically (at least 3 digits)
  width = max(3, len(str(len(plan))))
  print(f"\nTotal: {len(plan)} images -> {output_folder}")

  # 4. Warn before writing into a folder that already has files
  if output_folder.exists() and any(output_folder.iterdir()):
    answer = input(
        "The output folder is not empty. Files with the same names will be"
        " overwritten. Continue? (y/n): "
    ).strip().lower()
    if answer != "y":
      print("Cancelled. Nothing was copied.")
      return

  output_folder.mkdir(parents=True, exist_ok=True)

  # 5. Copy and rename sequentially, always starting from 1
  print()
  for number, (file, label) in enumerate(plan, start=1):
    new_name = f"{number:0{width}d}{file.suffix}"
    shutil.copy2(file, output_folder / new_name)
    print(f"Copied: [{label}] {file.name} -> {new_name}")

  print(
      "\nProcessing completed successfully! Your original files are safe and"
      " untouched."
  )

if __name__ == "__main__":
  manga_merger()