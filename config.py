"""Settings shared by the terminal app and the local web reader."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Folder that holds main.py. Data files (reader_progress.json, webp_converted.json,
# .reader_cache) stay here so existing progress survives the refactor.
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# Mother folder: one folder per author, each holding the manga folders.
MANGA_ROOT = Path(os.getenv("MANGA_ROOT", str(PROJECT_ROOT / "manga"))).expanduser()

# Where downloaded zip files are picked up from.
ZIP_SOURCE_FOLDER = Path(
    os.getenv("ZIP_SOURCE_FOLDER", str(Path.home() / "Downloads"))
).expanduser()

# ---------- downloader (admin) ----------
# API key from your nhentai account settings. It is only ever used by the local downloader server.
NHENTAI_API_KEY = os.getenv("NHENTAI_API_KEY", "").strip()
NHENTAI_API_BASE = os.getenv("NHENTAI_API_BASE", "https://nhentai.net/api/v2").strip().rstrip("/")
NHENTAI_USER_AGENT = os.getenv("NHENTAI_USER_AGENT", "MangaManager/1.0 (personal local tool)").strip()


def _split(text):
  return [part.strip() for part in text.replace("\n", ",").split(",") if part.strip()]


# Tags you never want to see in the downloader's results. Fill these in when you know the exact codes.
# Names are added to the search as -tag:"name"; numbers are tag ids and hide a result that carries them.
# Example:  NHENTAI_HIDE_TAGS=name one, name two, 12345
NHENTAI_HIDE_TAGS = _split(os.getenv("NHENTAI_HIDE_TAGS", ""))

# Requests per minute the downloader allows itself (the API page lists the real limits per endpoint).
# The defaults stay under the documented limits; the zip download limit is not documented, so it is cautious.
NHENTAI_LIMITS_PER_MINUTE = {
    "search": int(os.getenv("NHENTAI_SEARCH_PER_MINUTE", "12")),
    "detail": int(os.getenv("NHENTAI_DETAIL_PER_MINUTE", "30")),
    "cdn": int(os.getenv("NHENTAI_CDN_PER_MINUTE", "6")),
    "download": int(os.getenv("NHENTAI_DOWNLOAD_PER_MINUTE", "6")),
}
