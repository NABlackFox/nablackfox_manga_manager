
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from functions.convert_thumbnail import convert_thumbnails
from functions.grab_zip_files import grab_zip_files

from utils import (
    BOLD, DIM, YELLOW, RESET,
    clear_screen, print_header,
)


FUNCTIONS = {
    "1": "Convert thumbnail",
    "2": "Grab zip file",
}


def read_admin_choice():
    kb = KeyBindings()

    @kb.add("<any>")
    def _ignore(event):
        pass

    for key in FUNCTIONS:
        @kb.add(key, eager=True)
        def _pick(event, key=key):
            event.app.exit(result=key)

    @kb.add("escape", eager=True)
    def _back(event):
        event.app.exit(result="esc")

    return prompt("  > ", key_bindings=kb)


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

        choice = read_admin_choice()

        if choice == "esc":
            return

        if choice == "1":
            convert_thumbnails(manga_root)

        elif choice == "2":
            grab_zip_files(manga_root)
