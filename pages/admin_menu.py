from helpers.prompts import read_menu_choice
from functions.convert_to_webp import convert_to_webp
from functions.grab_zip_files import grab_zip_files
from functions.grab_zip_manual import grab_zip_manual

from utils import (
    BOLD, DIM, YELLOW, RESET,
    clear_screen, print_header,
)


FUNCTIONS = {
    "1": "Grab zip file",
    "2": "Grab zip file (manual mode)",
    "3": "Convert images to WebP",
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
            grab_zip_manual(manga_root)

        elif choice == "3":
            convert_to_webp(manga_root)