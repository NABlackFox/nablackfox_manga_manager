"""Small cached JPEG previews so the grids load fast."""
import hashlib
import io

from config import PROJECT_ROOT

try:
  from PIL import Image, ImageOps
except ImportError:
  Image = None

CACHE_FOLDER = PROJECT_ROOT / ".reader_cache"
THUMB_WIDTH = 360


def render_thumb(source, size=THUMB_WIDTH):
  """Small JPEG of an image, made on the spot. Nothing is saved to disk."""
  if Image is None:
    return source.read_bytes()
  with Image.open(source) as image:
    try:
      image.draft("RGB", (size * 2, size * 4))  # JPEG: decode at reduced size, much faster
    except Exception:
      pass
    image = ImageOps.exif_transpose(image)
    try:
      image.seek(0)
    except EOFError:
      pass
    image = image.convert("RGB")
    image.thumbnail((size, size * 2))
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=80)
  return out.getvalue()


def make_thumb(source):
  """Small cached JPEG of an image. Returns bytes."""
  stat = source.stat()
  key = hashlib.sha1(
      f"{source.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{THUMB_WIDTH}".encode()
  ).hexdigest()
  cached = CACHE_FOLDER / f"{key}.jpg"
  try:
    return cached.read_bytes()
  except OSError:
    pass

  if Image is None:
    return source.read_bytes()
  with Image.open(source) as image:
    image = ImageOps.exif_transpose(image)
    try:
      image.seek(0)
    except EOFError:
      pass
    image = image.convert("RGB")
    image.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 2))
    CACHE_FOLDER.mkdir(exist_ok=True)
    temp = cached.with_suffix(".tmp")
    image.save(temp, format="JPEG", quality=82)
    temp.replace(cached)
  return cached.read_bytes()
