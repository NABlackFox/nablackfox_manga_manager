import shutil
from pathlib import Path

from functions.grab_zip_files import ZIP_SOURCE_FOLDER
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings

from helpers.prompts import ask_merge_order, message_screen, read_confirm, pause
from pages.author_menu import print_author_grid
from utils import (
    BOLD, GREEN, RED, DIM, RESET,
    clear_screen, print_header, print_title, list_subfolders, natural_key,
)

TITLE = "Grab zip (manual)"
SCREEN_NAME = "Admin"


def list_zips(source_folder):
    """Every nhentai*.zip in the download folder, whatever the rest of the name."""
    try:
        zips = [
            f for f in source_folder.iterdir()
            if f.is_file()
            and f.suffix.casefold() == ".zip"
            and f.name.casefold().startswith("nhentai")
        ]
    except OSError:
        return None
    zips.sort(key=natural_key)
    return zips


def ask_author_by_name(authors, chosen, manga_root):
    """Same author picker as the main screen: type a name, Tab completes. None on Esc."""
    names = [folder.name for folder in authors]
    lookup = {name.casefold(): folder for name, folder in zip(names, authors)}
    completer = WordCompleter(names, ignore_case=True, match_middle=True, sentence=True)

    kb = KeyBindings()

    @kb.add("escape", eager=True)
    def _cancel(event):
        event.app.exit(result=None)

    error = ""
    while True:
        clear_screen()
        print_header(manga_root, f"Library: {manga_root}")
        print_title(TITLE, SCREEN_NAME)
        print(f"  {BOLD}ZIPs to move{RESET} {DIM}({len(chosen)}){RESET}\n")
        for zip_file in chosen:
            print(f"  {zip_file.name}")
        print(f"\n  {BOLD}Authors{RESET} {DIM}({len(names)}){RESET}\n")
        print_author_grid(names, manga_root)
        print(f"\n  {DIM}Type the author name (Tab to auto-complete).  Esc to cancel.{RESET}\n")
        if error:
            print(f"  {RED}{error}{RESET}\n")

        text = prompt("  Author > ", completer=completer, key_bindings=kb)
        if text is None:
            return None
        text = text.strip().strip('"\'')
        if text.casefold() in lookup:
            return lookup[text.casefold()]
        error = f'No author folder named "{text}". Try again.'


def grab_zip_manual(manga_root):
    """Pick ZIPs by hand, pick the author, move them. Repeats until done."""
    manga_root = Path(manga_root)
    source = ZIP_SOURCE_FOLDER

    if not source.is_dir():
        message_screen(
            SCREEN_NAME,
            [f"{RED}Download folder does not exist or is not accessible:{RESET}", str(source)],
            manga_root, TITLE,
        )
        return

    while True:
        zips = list_zips(source)
        if zips is None:
            message_screen(SCREEN_NAME, [f"{RED}Cannot read {source}{RESET}"], manga_root, TITLE)
            return
        if not zips:
            message_screen(SCREEN_NAME, ["No nhentai ZIP files left in the download folder."], manga_root, TITLE)
            return

        chosen = ask_merge_order(
            SCREEN_NAME, zips, manga_root, prompt_label="ZIP",
            title=TITLE, verb="moved", noun="ZIP", ordered=False, chosen_label="ZIPs to move",
            note=f"From: {GREEN}{source}{RESET}",
        )
        if chosen is None:
            return

        authors = list_subfolders(manga_root)
        if not authors:
            message_screen(SCREEN_NAME, ["No author folders found in the library."], manga_root, TITLE)
            return

        author_folder = ask_author_by_name(authors, chosen, manga_root)
        if author_folder is None:
            continue

        clear_screen()
        print_header(manga_root, f"Library: {manga_root}")
        print_title(TITLE, SCREEN_NAME)
        print(f"  Move {len(chosen)} ZIP(s) to {GREEN}{author_folder.name}{RESET}:\n")
        for zip_file in chosen:
            clash = (author_folder / zip_file.name).exists()
            note = f"  {RED}(already exists, will be skipped){RESET}" if clash else ""
            print(f"  {zip_file.name}{note}")
        print()

        if not read_confirm("  Continue? (y/n) "):
            print("\n  Cancelled. Nothing was moved.\n")
            pause()
            continue

        moved = failed = 0
        print()
        for zip_file in chosen:
            destination = author_folder / zip_file.name
            try:
                if destination.exists():
                    raise FileExistsError("destination already exists")
                shutil.move(str(zip_file), str(destination))
                print(f"  {GREEN}[MOVED]{RESET} {zip_file.name}")
                moved += 1
            except (OSError, shutil.Error) as exc:
                print(f"  {RED}[FAILED]{RESET} {zip_file.name}: {exc}")
                failed += 1

        print(f"\n  {GREEN}Moved: {moved}{RESET}  {RED}Failed: {failed}{RESET}\n")
        pause()