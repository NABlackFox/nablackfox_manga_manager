from pathlib import Path
import re
import shutil


def natural_key(path):
  """Sort key that orders names by the numbers inside them (2 before 10)."""
  return [
      int(part) if part.isdigit() else part.lower()
      for part in re.split(r"(\d+)", path.name)
  ]

def manga_page_converter():
  # 1. Get source directory path from user
  src_path_str = input(
      "Enter the path to the source folder containing the images: "
  ).strip().strip('"\'')
  if not src_path_str:
    print("Error: You must provide a valid source folder path.")
    return

  source_folder = Path(src_path_str)
  if not source_folder.exists() or not source_folder.is_dir():
    print("Error: The specified source folder does not exist.")
    return

  # 2. Get output directory path from user (or use default)
  default_output = source_folder.parent / "renamed_output"
  out_path_str = input(
      f"Enter the output folder path\n(Press Enter to default to 1 level higher"
      f" [{default_output}]): "
  ).strip().strip('"\'')

  if not out_path_str:
    output_folder = default_output
  else:
    output_folder = Path(out_path_str)

  # Create the output folder (and any necessary parent directories) safely
  output_folder.mkdir(parents=True, exist_ok=True)

  # 3. Get starting number from user
  try:
    start_num = int(input("Enter the starting number: "))
  except ValueError:
    print("Error: Please enter a valid integer for the starting number.")
    return

  # Supported image extensions
  image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

  # Find and sort all image files (natural sort: 1, 2, 3 ... 10, 11)
  files = [
      f
      for f in source_folder.iterdir()
      if f.is_file() and f.suffix.lower() in image_extensions
  ]
  files.sort(key=natural_key)

  if not files:
    print("No image files found in the specified source directory.")
    return

  print(
      f"\nFound {len(files)} images. Copying and renaming to:\n{output_folder}\n"
  )

  # 4. Copy and rename files sequentially
  current_num = start_num
  for file in files:
    ext = file.suffix
    # :03d pads the number with zeros (e.g., 001, 025). Change to :04d if you have over 999 pages.
    new_name = f"{current_num:03d}{ext}"
    new_path = output_folder / new_name

    # Copy the file safely, leaving original untouched
    shutil.copy2(file, new_path)
    print(f"Copied: {file.name} -> {new_name}")
    current_num += 1

  print(
      "\nProcessing completed successfully! Your original files are safe and"
      " untouched."
  )

if __name__ == "__main__":
  manga_page_converter()