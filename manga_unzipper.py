from pathlib import Path
import re
import shutil
import zipfile

META_FILE_NAME = "meta.json"

def natural_key(path):
  """Sort key that orders names by the numbers inside them (2 before 10)."""
  return [
      int(part) if part.isdigit() else part.lower()
      for part in re.split(r"(\d+)", path.name)
  ]

def clean_path(text):
  """Strip whitespace and surrounding quotes from a pasted path."""
  return text.strip().strip('"\'')

def list_zips(folder):
  """Return the zip files in a folder, sorted by the number in the name."""
  zips = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ".zip"]
  zips.sort(key=natural_key)
  return zips

def ask_for_author_folder():
  """Ask for the author folder that contains the downloaded zips."""
  while True:
    text = clean_path(input("Enter the author folder: "))
    if text and Path(text).is_dir():
      return Path(text)
    print("  Not a valid folder, try again.")

def unzip_one(zip_file, output_folder):
  """Unzip one zip into its own folder, delete meta.json, then delete the zip.

  If extraction fails, the half-extracted folder is removed and the zip is
  kept, so it is picked up again on the next run.
  """
  try:
    with zipfile.ZipFile(zip_file) as zf:
      zf.extractall(output_folder)
    (output_folder / META_FILE_NAME).unlink(missing_ok=True)
  except Exception:
    shutil.rmtree(output_folder, ignore_errors=True)
    raise

  # Only reached when the extraction fully succeeded
  zip_file.unlink()

def manga_unzipper():
  # 1. Ask for the author folder
  author_folder = ask_for_author_folder()

  # 2. Split the zips into new ones and ones that were already unzipped
  zips = list_zips(author_folder)
  to_unzip = [z for z in zips if not (author_folder / z.stem).exists()]
  skipped = len(zips) - len(to_unzip)

  print(f"\nFound {len(zips)} zip(s): {len(to_unzip)} new, {skipped} already unzipped.")

  if not to_unzip:
    print("Nothing to unzip.")
    return

  print("Each zip will be deleted after it is unzipped successfully.")
  answer = input("Continue? (y/n): ").strip().lower()
  if answer != "y":
    print("Cancelled. Nothing was changed.")
    return

  # 3. Unzip each new zip into its own folder, one by one
  print()
  failed = []
  for number, zip_file in enumerate(to_unzip, start=1):
    try:
      unzip_one(zip_file, author_folder / zip_file.stem)
      print(f"[{number}/{len(to_unzip)}] Unzipped: {zip_file.name}")
    except Exception as error:
      print(f"[{number}/{len(to_unzip)}] FAILED: {zip_file.name} ({error})")
      failed.append(zip_file.name)

  if failed:
    print(f"\nFinished with {len(failed)} failure(s):")
    for name in failed:
      print(f"  - {name}")
  else:
    print("\nProcessing completed successfully! The unzipped zip files were deleted.")


if __name__ == "__main__":
  manga_unzipper()