
from pathlib import Path
from PIL import Image, ImageOps
import os

from utils import IMAGE_EXTENSIONS, GREEN, YELLOW, RED, DIM, RESET


# Recognize only the first page's expected numeric names.
FIRST_PAGE_NAMES = {"1", "01", "001"}

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

    for name in ("1", "01", "001"):
        if name in candidates:
            # If multiple extensions share the same number,
            # choose a consistent filename order.
            return sorted(
                candidates[name],
                key=lambda p: (p.suffix.lower(), p.name.lower())
            )[0]

    return None


def convert_image_to_jpeg(source):
    """Convert one image to .jpeg, preserving its numeric filename."""
    target = source.with_suffix(".jpeg")

    # Already the required extension: no work needed.
    if source.suffix.lower() == ".jpeg":
        return "skipped", "already .jpeg"

    # Never overwrite another file.
    if target.exists():
        return "skipped", f"target already exists: {target.name}"

    # Temporary output stays in the same folder, so replacement is local.
    temp = source.with_name(source.stem + ".__thumbnail_tmp__.jpeg")

    try:
        with Image.open(source) as image:
            # Correct orientation based on EXIF metadata.
            image = ImageOps.exif_transpose(image)

            # Use the first frame if the source is animated.
            try:
                image.seek(0)
            except EOFError:
                pass

            image.load()

            # JPEG requires RGB or grayscale; flatten transparency onto white.
            if image.mode in ("RGBA", "LA") or (
                image.mode == "P" and "transparency" in image.info
            ):
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                output = background
            else:
                output = image.convert("RGB")

            output.save(temp, format="JPEG", quality=95)

        # Verify that the temporary output can be opened as a JPEG.
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

        return "failed", f"{source.name}: {exc}"


def convert_thumbnails(manga_root):
    """Scan author/chapter folders and convert each chapter's first image."""
    manga_root = Path(manga_root)

    converted = 0
    skipped = 0
    failed = 0
    no_image = 0

    print(f"\nScanning manga library: {manga_root}\n")

    try:
        author_folders = [
            folder for folder in manga_root.iterdir()
            if folder.is_dir() and not folder.name.startswith(".")
        ]
    except OSError as exc:
        print(f"{RED}Cannot read manga root: {exc}{RESET}")
        input("\nPress Enter to return...")
        return

    for author_folder in author_folders:
        try:
            chapter_folders = [
                folder for folder in author_folder.iterdir()
                if folder.is_dir() and not folder.name.startswith(".")
            ]
        except OSError as exc:
            print(f"{RED}[FAILED] {author_folder}: {exc}{RESET}")
            failed += 1
            continue

        for chapter_folder in chapter_folders:
            result = find_first_image(chapter_folder)

            if isinstance(result, tuple):
                print(f"{RED}[FAILED] {chapter_folder}: {result[1]}{RESET}")
                failed += 1
                continue

            if result is None:
                print(f"{DIM}[NO IMAGE] {chapter_folder}{RESET}")
                no_image += 1
                continue

            status, message = convert_image_to_jpeg(result)

            if status == "converted":
                print(f"{GREEN}[CONVERTED] {chapter_folder.name}: {message}{RESET}")
                converted += 1
            elif status == "skipped":
                print(f"{YELLOW}[SKIPPED] {chapter_folder.name}: {message}{RESET}")
                skipped += 1
            else:
                print(f"{RED}[FAILED] {chapter_folder.name}: {message}{RESET}")
                failed += 1

    print("\n" + "=" * 50)
    print("Thumbnail conversion summary")
    print("=" * 50)
    print(f"{GREEN}Converted: {converted}{RESET}")
    print(f"{YELLOW}Skipped:   {skipped}{RESET}")
    print(f"{DIM}No image:  {no_image}{RESET}")
    print(f"{RED}Failed:    {failed}{RESET}")
    print(f"Total chapters checked: {converted + skipped + no_image + failed}")

    input("\nPress Enter to return to the admin menu...")
