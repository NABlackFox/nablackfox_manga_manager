import sys

from config import MANGA_ROOT
from terminal.utils import RED, RESET, clear_screen, enable_ansi, print_header
from terminal.pages.author_menu import ask_for_author, run_author_menu
from terminal.pages.admin_menu import run_admin_menu
from terminal.pages.read_page import run_read_mode


def main():
  enable_ansi()

  if not MANGA_ROOT.is_dir():
    print(f"{RED}Library folder not found: {MANGA_ROOT}{RESET}")
    print("Set MANGA_ROOT in the .env file (or create a 'manga' folder) and try again.")
    sys.exit(1)

  try:
    while True:
      author = ask_for_author(MANGA_ROOT)
      if author is None:
        clear_screen()
        print_header(MANGA_ROOT, f"Library: {MANGA_ROOT}")
        print(f"  {RED}No author folders found in the library.{RESET}\n")
        return
      if author.casefold() == "admin":
        run_admin_menu(MANGA_ROOT)
      elif author.casefold() == "read":
        run_read_mode(MANGA_ROOT)
      else:
        run_author_menu(author, MANGA_ROOT)
  except (KeyboardInterrupt, EOFError):
    pass

  clear_screen()
  print("Goodbye!")


if __name__ == "__main__":
  main()
