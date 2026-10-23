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

def list_zips(folder):
  """Return the zip files in a folder, sorted by the number in the name."""
  zips = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ".zip"]
  zips.sort(key=natural_key)
  return zips

def find_new_zips(folder):
  """Return (zips still to unzip, number already unzipped).

  A zip counts as already unzipped when a folder with its name exists.
  """
  zips = list_zips(folder)
  to_unzip = [z for z in zips if not (folder / z.stem).exists()]
  return to_unzip, len(zips) - len(to_unzip)

def unzip_one(zip_file, output_folder):
  """Unzip one zip into its own folder, delete meta.json, then delete the zip.

  If extraction fails (or is interrupted with Ctrl+C), the half-extracted
  folder is removed and the zip is kept, so it is picked up again next time.
  """
  try:
    with zipfile.ZipFile(zip_file) as zf:
      zf.extractall(output_folder)
    (output_folder / META_FILE_NAME).unlink(missing_ok=True)
  except BaseException:
    shutil.rmtree(output_folder, ignore_errors=True)
    raise

  # Only reached when the extraction fully succeeded
  zip_file.unlink()

def unzip_zips(folder, zips):
  """Unzip each zip into its own folder inside `folder`, one by one.

  Yields (number, zip_file, error) after every zip, so the caller can show
  progress. `error` is None on success, or the exception on failure.
  """
  for number, zip_file in enumerate(zips, start=1):
    try:
      unzip_one(zip_file, folder / zip_file.stem)
      error = None
    except Exception as exc:
      error = exc
    yield number, zip_file, error