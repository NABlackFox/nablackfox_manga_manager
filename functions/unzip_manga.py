from pathlib import PurePosixPath
import shutil
import zipfile
from utils import natural_key

META_FILE_NAME = "meta.json"

def list_zips(folder):
  """Return the zip files in a folder, sorted by the number in the name."""
  try:
    zips = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ".zip"]
  except OSError:
    return []
  zips.sort(key=natural_key)
  return zips

def find_new_zips(folder):
  """Return (zips still to unzip, number already unzipped)."""
  zips = list_zips(folder)
  to_unzip = [z for z in zips if not (folder / z.stem).exists()]
  return to_unzip, len(zips) - len(to_unzip)

def extract_flat(zf, output_folder):
  """Extract an open zip into output_folder."""
  infos = [i for i in zf.infolist() if i.filename.strip("/")]
  all_parts = [PurePosixPath(i.filename).parts for i in infos]

  if any(".." in parts or PurePosixPath(i.filename).is_absolute()
         for parts, i in zip(all_parts, infos)):
    raise ValueError("zip contains an unsafe path")

  roots = {parts[0] for parts in all_parts}
  has_top_level_file = any(
      len(parts) == 1 and not i.is_dir() for parts, i in zip(all_parts, infos)
  )
  skip = 1 if len(roots) == 1 and not has_top_level_file else 0

  output_folder.mkdir(parents=True, exist_ok=True)
  for info, parts in zip(infos, all_parts):
    parts = parts[skip:]
    if not parts:
      continue
    target = output_folder.joinpath(*parts)
    if info.is_dir():
      target.mkdir(parents=True, exist_ok=True)
      continue
    target.parent.mkdir(parents=True, exist_ok=True)
    with zf.open(info) as source, open(target, "wb") as destination:
      shutil.copyfileobj(source, destination)

def unzip_one(zip_file, output_folder):
  """Unzip one zip into its own folder, delete meta.json, then delete the zip."""
  try:
    with zipfile.ZipFile(zip_file) as zf:
      extract_flat(zf, output_folder)
    (output_folder / META_FILE_NAME).unlink(missing_ok=True)
  except BaseException:
    shutil.rmtree(output_folder, ignore_errors=True)
    raise
  zip_file.unlink()

def unzip_zips(folder, zips):
  """Unzip each zip into its own folder inside `folder`, one by one."""
  for number, zip_file in enumerate(zips, start=1):
    try:
      unzip_one(zip_file, folder / zip_file.stem)
      error = None
    except Exception as exc:
      error = exc
    yield number, zip_file, error