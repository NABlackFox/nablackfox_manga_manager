from pathlib import Path
from PIL import Image, ImageOps
import json
import os

from utils import (
    IMAGE_EXTENSIONS, GREEN, YELLOW, RED, DIM, RESET,
    list_subfolders, natural_key,
)


TARGET_EXT = ".webp"
WEBP_QUALITY = 90          # 90 = visually identical, still much smaller than jpg/png
TEMP_TAG = ".__webp_tmp__"  # marks half-written files so they can be cleaned up

# Remembers which chapter folders are already fully converted.
MARKER_FILE = Path(__file__).resolve().parent.parent / "webp_converted.json"


# Recognize only the first page's expected names, in priority order.
# Plain numbers come first; the "-chapter1" ones are the first page of a
# merged folder that has chapter markers (e.g. 001-chapter1.png).
FIRST_PAGE_NAMES = (
    "1", "01", "001",
    "1-chapter1", "01-chapter1", "001-chapter1",
)

def find_first_image(chapter_folder):
    """Find the first page using a fixed filename priority."""
    candidates = {}

    try:
        with os.scandir(chapter_folder) as entries:
            for entry in entries:
                if not entry.is_file():
                    continue

                path = Path(entry.name)

                if path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue

                if path.stem in FIRST_PAGE_NAMES:
                    candidates.setdefault(path.stem, []).append(
                        chapter_folder / entry.name
                    )

    except OSError as exc:
        return None, str(exc)

    for name in FIRST_PAGE_NAMES:
        if name in candidates:
            # If multiple extensions share the same number,
            # choose a consistent filename order.
            return sorted(
                candidates[name],
                key=lambda p: (p.suffix.lower(), p.name.lower())
            )[0]

    return None


# ---------- converted-folder markers ----------
# webp_converted.json looks like:
#   {"root": "D:/manga", "folders": {"AuthorA/Chapter 1": {"mtime": 1730000000000000000}}}
# The mtime is the folder's "last changed" stamp taken right after conversion.
# If pages are added/removed later the stamp changes, so the folder is checked again.

def load_markers(manga_root):
    try:
        data = json.loads(MARKER_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

    # Marker file belongs to another library location: start fresh.
    if not isinstance(data, dict) or data.get("root") != str(manga_root):
        return {}

    folders = data.get("folders")
    return folders if isinstance(folders, dict) else {}


def save_markers(manga_root, markers):
    temp = MARKER_FILE.with_suffix(".tmp")
    try:
        temp.write_text(
            json.dumps({"root": str(manga_root), "folders": markers},
                       indent=1, ensure_ascii=False),
            encoding="utf-8",
        )
        temp.replace(MARKER_FILE)
    except OSError as exc:
        print(f"{RED}Could not save {MARKER_FILE.name}: {exc}{RESET}")


def prune_markers(manga_root, markers):
    """Drop markers whose folder no longer exists. Returns how many were removed."""
    gone = [key for key in markers if not (manga_root / key).is_dir()]
    for key in gone:
        del markers[key]
    return len(gone)


def folder_stamp(folder):
    try:
        return folder.stat().st_mtime_ns
    except OSError:
        return None


# ---------- conversion ----------

def convert_image_to_webp(source):
    """Convert one image to .webp, keeping its filename (001.png -> 001.webp).

    Returns (status, message). status is one of:
    "already" (is .webp), "skipped" (needs a look), "converted", "failed".
    """
    if source.suffix.lower() == TARGET_EXT:
        return "already", "already .webp"

    target = source.with_suffix(TARGET_EXT)

    # Never overwrite another file (e.g. 001.png and 001.jpg both present).
    if target.exists():
        return "skipped", f"{source.name}: {target.name} already exists"

    temp = source.with_name(source.stem + TEMP_TAG + TARGET_EXT)

    try:
        with Image.open(source) as image:
            # Animated files would lose their animation: leave them alone.
            if getattr(image, "is_animated", False):
                return "skipped", f"{source.name}: animated image"

            image = ImageOps.exif_transpose(image)
            image.load()

            # Keep transparency if there is any, otherwise plain RGB.
            has_alpha = image.mode in ("RGBA", "LA") or (
                image.mode == "P" and "transparency" in image.info
            )
            output = image.convert("RGBA" if has_alpha else "RGB")

            output.save(temp, format="WEBP", quality=WEBP_QUALITY, method=4)

        # Verify that the temporary output can be opened.
        with Image.open(temp) as check:
            check.verify()

        # Publish the converted image only after successful verification.
        temp.replace(target)

        # Delete the original only after the new file exists and is valid.
        source.unlink()

        return "converted", f"{source.name} -> {target.name}"

    except Exception as exc:
        try:
            if temp.exists():
                temp.unlink()
        except OSError:
            pass

        # WebP cannot store images taller/wider than 16383 px.
        return "failed", f"{source.name}: {exc}"


def convert_folder(folder, label):
    """Convert every image directly inside `folder`.

    Returns (converted, skipped, failed). Prints only what needs attention.
    """
    converted = skipped = failed = 0

    try:
        files = [f for f in folder.iterdir() if f.is_file()]
    except OSError as exc:
        print(f"{RED}[FAILED] {label}: {exc}{RESET}")
        return 0, 0, 1

    for file in sorted(files, key=natural_key):
        # Leftover from an interrupted run: remove it.
        if TEMP_TAG in file.name:
            try:
                file.unlink()
            except OSError:
                pass
            continue

        if file.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        status, message = convert_image_to_webp(file)

        if status == "converted":
            converted += 1
        elif status == "skipped":
            print(f"{YELLOW}[SKIPPED] {label}: {message}{RESET}")
            skipped += 1
        elif status == "failed":
            print(f"{RED}[FAILED] {label}: {message}{RESET}")
            failed += 1

    return converted, skipped, failed


def convert_to_webp(manga_root):
    """Convert every image in the library to .webp, remembering finished folders."""
    manga_root = Path(manga_root)

    converted = skipped = failed = 0
    folders_done = 0      # converted/checked in this run
    folders_marked = 0    # skipped because a marker says "already converted"

    print(f"\nScanning manga library: {manga_root}\n")

    try:
        author_folders = list_subfolders(manga_root)
    except OSError as exc:
        print(f"{RED}Cannot read manga root: {exc}{RESET}")
        input("\nPress Enter to return...")
        return

    markers = load_markers(manga_root)

    # Folders that were deleted since the last run lose their marker.
    removed = prune_markers(manga_root, markers)
    if removed:
        print(f"{DIM}Removed {removed} marker(s) of deleted folders.{RESET}\n")

    try:
        for author_folder in author_folders:
            # An image sitting directly in the author folder (the author thumbnail).
            c, s, f = convert_folder(author_folder, author_folder.name)
            converted += c
            skipped += s
            failed += f

            for chapter_folder in list_subfolders(author_folder):
                key = chapter_folder.relative_to(manga_root).as_posix()
                stamp = folder_stamp(chapter_folder)

                # Marker matches and the folder has not changed: do not touch it.
                if stamp is not None and markers.get(key, {}).get("mtime") == stamp:
                    folders_marked += 1
                    continue

                c, s, f = convert_folder(chapter_folder, key)
                converted += c
                skipped += s
                failed += f
                folders_done += 1

                if c:
                    print(f"{GREEN}[CONVERTED] {key}: {c} image(s){RESET}")

                if s == 0 and f == 0:
                    # Everything is .webp now: remember it (stamp taken AFTER
                    # converting, because renaming files changes the folder).
                    markers[key] = {"mtime": folder_stamp(chapter_folder)}
                else:
                    markers.pop(key, None)  # problem found: check again next time
    finally:
        # Saved even if you press Ctrl+C halfway.
        save_markers(manga_root, markers)

    print("\n" + "=" * 50)
    print("WebP conversion summary")
    print("=" * 50)
    print(f"{GREEN}Images converted:      {converted}{RESET}")
    print(f"{YELLOW}Images skipped:        {skipped}{RESET}")
    print(f"{RED}Images failed:         {failed}{RESET}")
    print(f"Folders checked:       {folders_done}")
    print(f"{DIM}Folders already done:  {folders_marked}{RESET}")
    print(f"{DIM}Markers removed:       {removed}{RESET}")

    input("\nPress Enter to return to the admin menu...")