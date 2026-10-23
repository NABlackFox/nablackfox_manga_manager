
import re
import shutil
from collections import defaultdict
from pathlib import Path

from utils import GREEN, YELLOW, RED, DIM, RESET


# TODO: Change this to the folder where your downloaded ZIP files are stored.
ZIP_SOURCE_FOLDER = Path(r"C:\Users\M16r2\Downloads")


def normalize_name(name):
    """Normalize text for case-insensitive, punctuation-tolerant matching."""
    return " ".join(re.findall(r"[a-z0-9]+", name.casefold()))


def extract_author_text(filename):
    """
    Extract the first bracket group after the nhentai ID.

    Example:
    nhentai-516648 - [Gasoline Chahan (Edogawa Nitro King)] ...
    -> Gasoline Chahan (Edogawa Nitro King)
    """
    match = re.match(
        r"^nhentai-\d+\s*-\s*\[([^\]]+)\]",
        filename,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1)



def extract_author_candidates(filename):
    """
    Extract author candidates from the first bracket group.

    [Fan no Hitori] -> ["Fan no Hitori"]
    [Gasoline Chahan (Edogawa Nitro King)]
        -> ["Gasoline Chahan", "Edogawa Nitro King"]
    """
    match = re.match(
        r"^nhentai-\d+\s*-\s*\[([^\]]+)\]",
        filename,
        flags=re.IGNORECASE,
    )

    if not match:
        return []

    group = match.group(1).strip()

    # If parentheses exist, try A first, then B.
    # Otherwise, the whole group is the only candidate.
    parenthesized = re.search(r"\(([^()]*)\)", group)

    if parenthesized:
        candidate_a = group[:parenthesized.start()].strip()
        candidate_b = parenthesized.group(1).strip()

        return [
            candidate for candidate in (candidate_a, candidate_b)
            if candidate
        ]

    return [group]



def find_matching_author(filename, author_folders):
    """Check candidate A first, then candidate B using safe prefix matching."""
    candidates = extract_author_candidates(filename)

    for index, candidate in enumerate(candidates):
        normalized_candidate = normalize_name(candidate)

        matching_folders = []

        for folder in author_folders:
            normalized_folder = normalize_name(folder.name)

            if not normalized_folder:
                continue

            if index == 0:
                # Candidate A: require an exact match.
                matches = normalized_candidate == normalized_folder
            else:
                # Candidate B: folder name must be the beginning
                # of the candidate, followed by a word boundary.
                matches = (
                    normalized_candidate == normalized_folder
                    or normalized_candidate.startswith(normalized_folder + " ")
                )

            if matches:
                matching_folders.append(folder)

        if matching_folders:
            # If multiple folders match, prefer the longest folder name.
            return max(
                matching_folders,
                key=lambda folder: len(normalize_name(folder.name)),
            )

    return None

def grab_zip_files(manga_root):
    manga_root = Path(manga_root)
    source_folder = ZIP_SOURCE_FOLDER

    if not source_folder.is_dir():
        print(
            f"{RED}Download folder does not exist or is not accessible:"
            f"\n{source_folder}{RESET}"
        )
        input("\nPress Enter to return to the admin menu...")
        return

    try:
        author_folders = [
            folder
            for folder in manga_root.iterdir()
            if folder.is_dir() and not folder.name.startswith(".")
        ]

        zip_files = [
            file
            for file in source_folder.iterdir()
            if file.is_file()
            and file.suffix.casefold() == ".zip"
            and file.name.casefold().startswith("nhentai")
        ]

    except OSError as exc:
        print(f"{RED}Cannot scan a folder: {exc}{RESET}")
        input("\nPress Enter to return to the admin menu...")
        return

    # Matched files are grouped by the actual existing author folder.
    matched = defaultdict(list)
    unmatched = []

    for zip_file in sorted(zip_files, key=lambda p: p.name.casefold()):
        author_folder = find_matching_author(zip_file.name, author_folders)

        if author_folder is None:
            unmatched.append((zip_file, "no matching author"))
            continue
        destination = author_folder / zip_file.name

        # Never overwrite an existing file.
        if destination.exists():
            unmatched.append((zip_file, "destination file already exists"))
            continue

        matched[author_folder].append(zip_file)

    # Preview the entire plan before moving anything.
    print(f"\n{GREEN}ZIP files found: {len(zip_files)}{RESET}")
    print(f"Download folder: {source_folder}\n")

    for author_folder in sorted(
        matched, key=lambda folder: folder.name.casefold()
    ):
        print(f"{GREEN}{author_folder.name}:{RESET}")

        for zip_file in matched[author_folder]:
            print(f"  {zip_file.name}")

        print()

    print(f"{YELLOW}None Match:{RESET}")

    if unmatched:
        for zip_file, reason in unmatched:
            print(f"  {zip_file.name} ({reason})")
    else:
        print("  None")

    total_matched = sum(len(files) for files in matched.values())

    print(f"\nMatched ZIP files: {total_matched}")
    print(f"Unmatched / conflicts: {len(unmatched)}")

    if not zip_files:
        print(f"\n{DIM}No matching ZIP files were found.{RESET}")
        input("\nPress Enter to return to the admin menu...")
        return

    if total_matched == 0:
        print(f"\n{YELLOW}Nothing can be moved safely.{RESET}")
        input("\nPress Enter to return to the admin menu...")
        return

    # One confirmation controls the entire operation.
    answer = input(
        f"\nMove these {total_matched} ZIP file(s) "
        "to their author folders? [y/N]: "
    ).strip().casefold()

    if answer != "y":
        print(f"\n{YELLOW}Operation cancelled. No files moved.{RESET}")
        input("\nPress Enter to return to the admin menu...")
        return

    moved = 0
    failed = 0

    print("\nMoving files...\n")

    for author_folder, files in matched.items():
        for zip_file in files:
            destination = author_folder / zip_file.name

            try:
                # Recheck immediately before moving.
                if destination.exists():
                    raise FileExistsError(
                        f"Destination already exists: {destination}"
                    )

                shutil.move(str(zip_file), str(destination))

                print(
                    f"{GREEN}[MOVED] {zip_file.name} "
                    f"-> {author_folder.name}{RESET}"
                )
                moved += 1

            except Exception as exc:
                print(f"{RED}[FAILED] {zip_file.name}: {exc}{RESET}")
                failed += 1

    print("\n" + "=" * 45)
    print("ZIP grabbing summary")
    print("=" * 45)
    print(f"{GREEN}Moved:  {moved}{RESET}")
    print(f"{RED}Failed: {failed}{RESET}")
    print(f"{YELLOW}Left in download folder: "
          f"{len(unmatched) + failed}{RESET}")

    input("\nPress Enter to return to the admin menu...")
