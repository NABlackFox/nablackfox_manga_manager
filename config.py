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
