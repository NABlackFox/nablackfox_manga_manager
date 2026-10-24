from helpers.prompts import read_menu_choice
from functions.convert_thumbnail import convert_thumbnails
from functions.grab_zip_files import grab_zip_files

from utils import (
    BOLD, DIM, YELLOW, RESET,
    clear_screen, print_header,
)


FUNCTIONS = {
    "1": "Grab zip file",
    "2": "Convert thumbnail",
}


def run_admin_menu(manga_root):
    while True:
        clear_screen()
        print_header(manga_root, f"Library: {manga_root}")

        print(f"  {BOLD}Admin menu{RESET}\n")

        for key, name in FUNCTIONS.items():
            print(f"  {YELLOW}{key}{RESET}  {name}")

        print(
            f"\n  {DIM}Press 1-{len(FUNCTIONS)} to choose, "
            f"Esc to return, Ctrl+C to exit.{RESET}\n"
        )

        choice = read_menu_choice(FUNCTIONS)

        if choice == "esc":
            return

        if choice == "1":
            grab_zip_files(manga_root)

        elif choice == "2":
            convert_thumbnails(manga_root)