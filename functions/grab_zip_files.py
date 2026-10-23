import os
from dotenv import load_dotenv
import re
import shutil
from collections import defaultdict
from pathlib import Path

from utils import GREEN, YELLOW, RED, DIM, RESET


# TODO: Change this to the folder where your downloaded ZIP files are stored.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

ZIP_SOURCE_FOLDER = Path(
    os.getenv("ZIP_SOURCE_FOLDER", str(Path.home() / "Downloads"))
).expanduser()

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

def prompt_create_missing_author_folders(unmatched, manga_root):
    """Offer to create folders for unique unmatched authors."""

    groups = {}

    # Only offer folder creation for missing authors, not file conflicts.
    for zip_file, reason in unmatched:
        if reason != "no matching author":
            continue

        candidates = extract_author_candidates(zip_file.name)
        if not candidates:
            continue

        key = tuple(normalize_name(name) for name in candidates)

        if key not in groups:
            groups[key] = {
                "candidates": candidates,
                "files": [],
            }

        groups[key]["files"].append(zip_file)

    if not groups:
        return

    print(f"\n{YELLOW}{'=' * 45}{RESET}")
    print(f"{YELLOW}CREATE MISSING AUTHOR FOLDERS{RESET}")
    print(f"{YELLOW}Found {len(groups)} possible new author(s).{RESET}")
    print(f"{YELLOW}{'=' * 45}{RESET}")

    created_count = 0

    for group in groups.values():
        candidates = group["candidates"]
        files = group["files"]

        print(f"\n{DIM}{'-' * 45}{RESET}")
        print(f"{GREEN}ZIP files for this author: {len(files)}{RESET}")

        for zip_file in files:
            print(f"  {zip_file.name}")

        answer = input(
            f"\n{YELLOW}Create a folder for these ZIPs? [y/N]: {RESET}"
        ).strip().casefold()

        if answer != "y":
            print(f"{DIM}Skipped.{RESET}")
            continue

        print(f"\n{GREEN}Choose the folder name:{RESET}")
        print(f"  1. Candidate A: {candidates[0]}")

        if len(candidates) > 1:
            print(f"  2. Candidate B: {candidates[1]}")

        print("  3. Enter a custom folder name")
        print("  0. Skip")

        while True:
            choice = input("Your choice: ").strip()

            if choice == "0":
                print(f"{DIM}Skipped.{RESET}")
                break

            if choice == "1":
                folder_name = candidates[0]

            elif choice == "2" and len(candidates) > 1:
                folder_name = candidates[1]

            elif choice == "3":
                # Keep asking for a custom name until it is valid.
                while True:
                    folder_name = input(
                        "Enter custom folder name: "
                    ).strip()

                    if not folder_name:
                        print(f"{RED}Folder name cannot be empty.{RESET}")
                        continue

                    normalized_custom = normalize_name(folder_name)
                    normalized_a = normalize_name(candidates[0])

                    valid_name = normalized_custom == normalized_a

                    if len(candidates) > 1:
                        normalized_b = normalize_name(candidates[1])
                        valid_name = valid_name or (
                            normalized_b == normalized_custom
                            or normalized_b.startswith(
                                normalized_custom + " "
                            )
                        )

                    if valid_name:
                        break

                    print(
                        f"{RED}That name won't match these ZIPs "
                        f"on the next run.{RESET}"
                    )
                    print(
                        f"{DIM}Use Candidate A exactly, or a whole-word "
                        f"prefix of Candidate B.{RESET}"
                    )

            else:
                print(f"{RED}Invalid choice. Try again.{RESET}")
                continue

            normalized_name = normalize_name(folder_name)

            existing_folder = next(
                (
                    folder
                    for folder in manga_root.iterdir()
                    if folder.is_dir()
                    and normalize_name(folder.name) == normalized_name
                ),
                None,
            )

            if existing_folder:
                print(
                    f"{YELLOW}Folder already exists: "
                    f"{existing_folder.name}{RESET}"
                )
                print(
                    f"{DIM}No folder created for this author.{RESET}"
                )
                break

            try:
                (manga_root / folder_name).mkdir()
                print(f"{GREEN}[CREATED] Folder: {folder_name}{RESET}")
                print(f"{DIM}ZIP files have NOT been moved.{RESET}")
                created_count += 1

            except OSError as exc:
                print(f"{RED}[FAILED] Could not create folder: {exc}{RESET}")

            break

    if created_count:
        print(f"\n{GREEN}{'=' * 45}{RESET}")
        print(f"{GREEN}Created {created_count} author folder(s).{RESET}")
        print(
            f"{YELLOW}NEXT STEP: Return to the Admin menu "
            f"and select Option 2 - Grab zip file again.{RESET}"
        )
        print(
            f"{DIM}The ZIPs will be checked again and moved only "
            f"if they match. Nothing else will move automatically.{RESET}"
        )
        print(f"{GREEN}{'=' * 45}{RESET}")

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
        # Still offer to create folders for unmatched new authors.
        prompt_create_missing_author_folders(unmatched, manga_root)
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

    prompt_create_missing_author_folders(unmatched, manga_root)

    input("\nPress Enter to return to the admin menu...")
