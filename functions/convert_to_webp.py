from pathlib import Path
from PIL import Image, ImageOps
import json
import os
import shutil

from utils import (
    IMAGE_EXTENSIONS, GREEN, YELLOW, RED, DIM, RESET,
    list_subfolders, natural_key,
)


TARGET_EXT = ".webp"
WEBP_QUALITY = 80          # 90 = visually identical, still much smaller than jpg/png
TEMP_TAG = ".__webp_tmp__"  # marks half-written files so they can be cleaned up
BAR_WIDTH = 20             # width of the progress bar, in characters

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


# ---------- terminal output ----------

def fit(text):
    """Cut a line so it never wraps (a wrapped line breaks the progress bar)."""
    width = shutil.get_terminal_size().columns - 1
    return text if len(text) <= width else text[: width - 3] + "..."


def show_progress(index, total, key, done, count):
    """Redraw one line:  [3/120] [########------------] 8/20  Author/Chapter"""
    if count == 0:
        line = fit(f"[{index}/{total}] CHECKING  {key}")
    else:
        filled = BAR_WIDTH * done // count
        bar = "#" * filled + "-" * (BAR_WIDTH - filled)
        line = fit(f"[{index}/{total}] [{bar}] {done}/{count}  {key}")
    print(f"\r\033[K{line}", end="", flush=True)


def show_final(color, text):
    """Replace the current progress line with a finished line."""
    print(f"\r\033[K{color}{fit(text)}{RESET}")


def convert_folder(folder, label, on_progress=None):
    """Convert every image directly inside `folder`.

    Returns (converted, skipped, failed, issues). `issues` is a list of
    (color, text) lines for the caller to print once the progress bar is done.
    on_progress(done, total) is called before the first image and after each one.
    """
    converted = skipped = failed = 0
    issues = []

    try:
        files = sorted((f for f in folder.iterdir() if f.is_file()), key=natural_key)
    except OSError as exc:
        return 0, 0, 1, [(RED, f"    [FAILED] {label}: {exc}")]

    todo = []
    for file in files:
        # Leftover from an interrupted run: remove it.
        if TEMP_TAG in file.name:
            try:
                file.unlink()
            except OSError:
                pass
            continue

        # Only images that are not .webp yet need work.
        if (file.suffix.lower() in IMAGE_EXTENSIONS
                and file.suffix.lower() != TARGET_EXT):
            todo.append(file)

    if on_progress and todo:
        on_progress(0, len(todo))

    for number, file in enumerate(todo, start=1):
        status, message = convert_image_to_webp(file)

        if status == "converted":
            converted += 1
        elif status == "skipped":
            issues.append((YELLOW, f"    [SKIPPED] {message}"))
            skipped += 1
        elif status == "failed":
            issues.append((RED, f"    [FAILED] {message}"))
            failed += 1

        if on_progress:
            on_progress(number, len(todo))

    return converted, skipped, failed, issues


def convert_to_webp(manga_root):
    """Convert every image in the library to .webp, remembering finished folders."""
    manga_root = Path(manga_root)

    converted = skipped = failed = 0
    folders_converted = 0   # folders where work was done
    folders_clean = 0       # folders checked, nothing to convert
    folders_marked = 0      # skipped because a marker says "already converted"
    folders_problem = 0     # folders with skipped/failed images

    print(f"\nScanning manga library: {manga_root}\n")

    try:
        author_folders = list_subfolders(manga_root)
    except OSError as exc:
        print(f"{RED}Cannot read manga root: {exc}{RESET}")
        input("\nPress Enter to return...")
        return

    # Step 1: forget markers of folders that were deleted.
    markers = load_markers(manga_root)
    gone = [key for key in markers if not (manga_root / key).is_dir()]
    for key in gone:
        del markers[key]
        print(f"{YELLOW}[MARKER REMOVED] {key} (folder no longer exists){RESET}")
    removed = len(gone)
    if removed:
        print()

    # Step 2: list every chapter folder first, so we can show "3/120".
    chapters = [
        (author, chapter)
        for author in author_folders
        for chapter in list_subfolders(author)
    ]
    total = len(chapters)
    print(f"Found {len(author_folders)} author folder(s), {total} chapter folder(s).\n")

    try:
        # Images sitting directly in an author folder (the author thumbnail).
        for author in author_folders:
            c, s, f, issues = convert_folder(author, author.name)
            converted += c
            skipped += s
            failed += f
            if c:
                print(f"{GREEN}[AUTHOR IMAGE] {author.name}: {c} converted{RESET}")
            for color, text in issues:
                print(f"{color}{text}{RESET}")

        # Step 3: the chapter folders.
        for index, (author, chapter) in enumerate(chapters, start=1):
            key = chapter.relative_to(manga_root).as_posix()
            stamp = folder_stamp(chapter)

            # Marker matches and the folder has not changed: do not touch it.
            if stamp is not None and markers.get(key, {}).get("mtime") == stamp:
                folders_marked += 1
                print(f"{DIM}[{index}/{total}] SKIP    {fit(key)}  (already converted){RESET}")
                continue

            show_progress(index, total, key, 0, 0)

            c, s, f, issues = convert_folder(
                chapter, key,
                on_progress=lambda done, count: show_progress(index, total, key, done, count),
            )
            converted += c
            skipped += s
            failed += f

            if s or f:
                folders_problem += 1
                show_final(YELLOW, f"[{index}/{total}] ISSUES  {key}: "
                                   f"{c} converted, {s} skipped, {f} failed")
                markers.pop(key, None)  # check again next time
            elif c:
                folders_converted += 1
                show_final(GREEN, f"[{index}/{total}] DONE    {key}: {c} converted")
            else:
                folders_clean += 1
                show_final(DIM, f"[{index}/{total}] OK      {key}  (nothing to convert)")

            for color, text in issues:
                print(f"{color}{text}{RESET}")

            if not (s or f):
                # Stamp taken AFTER converting, because renaming files changes it.
                markers[key] = {"mtime": folder_stamp(chapter)}
    finally:
        # Saved even if you press Ctrl+C halfway.
        save_markers(manga_root, markers)

    print("\n" + "=" * 50)
    print("WebP conversion summary")
    print("=" * 50)
    print(f"{GREEN}Images converted:        {converted}{RESET}")
    print(f"{YELLOW}Images skipped:          {skipped}{RESET}")
    print(f"{RED}Images failed:           {failed}{RESET}")
    print(f"Folders converted:       {folders_converted}")
    print(f"Folders with issues:     {folders_problem}")
    print(f"{DIM}Folders nothing to do:   {folders_clean}{RESET}")
    print(f"{DIM}Folders already marked:  {folders_marked}{RESET}")
    print(f"{DIM}Markers removed:         {removed}{RESET}")

    input("\nPress Enter to return to the admin menu...")