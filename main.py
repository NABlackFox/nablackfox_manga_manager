import sys

from config import MANGA_ROOT
from terminal.shared.utils import (
    BOLD, DIM, RED, RESET, YELLOW, clear_screen, enable_ansi, print_header,
)
from terminal.shared.prompts import read_menu_choice
from terminal.author_menu.author_menu import BACK, ask_for_author, run_author_menu
from terminal.admin_menu.admin_menu import run_admin_menu
from terminal.read_page.read_page import run_read_mode
from terminal.download_page.download_page import run_download_mode

USAGE = """Manga library

Usage:
  python main.py            ask what to do (1 = read, 2 = manager, 3 = download)
  python main.py read       open the library in the browser straight away
  python main.py manage     open the manager straight away
  python main.py download   open the downloader straight away

Also accepted: -read  --read  -r   |   -manage  --manage  -manager  --manager  -m
               -download  --download  -d
On Windows you can type  py main.py read  instead of  python main.py read.
"""

# every spelling of an argument -> "read", "manage" or "download"
ALIASES = {
    "read": "read", "r": "read",
    "manage": "manage", "manager": "manage", "m": "manage",
    "download": "download", "downloader": "download", "d": "download",
}


def parse_mode(args):
  """'read', 'manage', 'download' or None (ask). Exits with a short help text for -h or something unknown."""
  if not args:
    return None
  word = args[0].lstrip("-").casefold()
  if word in ("h", "help"):
    print(USAGE)
    sys.exit(0)
  if word in ALIASES and len(args) == 1:
    return ALIASES[word]
  print(f"{RED}Unknown argument: {' '.join(args)}{RESET}\n")
  print(USAGE)
  sys.exit(2)


def ask_mode():
  """The start menu. Returns 'read', 'manage', 'download', or None to quit (Esc)."""
  clear_screen()
  print_header(MANGA_ROOT, f"Library: {MANGA_ROOT}")
  print(f"  {BOLD}What do you want to do?{RESET}\n")
  print(f"  {YELLOW}1{RESET}  Read      {DIM}open the library in your browser{RESET}")
  print(f"  {YELLOW}2{RESET}  Manager   {DIM}unzip, merge and edit manga{RESET}")
  print(f"  {YELLOW}3{RESET}  Download  {DIM}search an author and download zips{RESET}")
  print(f"\n  {DIM}Press 1, 2 or 3. Esc or Ctrl+C to exit.{RESET}\n")
  choice = read_menu_choice(("1", "2", "3"))
  return {"1": "read", "2": "manage", "3": "download"}.get(choice)


def run_manager():
  """The author list and everything behind it. Returns when you press Esc on the author list."""
  while True:
    author = ask_for_author(MANGA_ROOT)
    if author is BACK:
      return
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


def main():
  forced = parse_mode(sys.argv[1:])
  enable_ansi()

  if not MANGA_ROOT.is_dir():
    print(f"{RED}Library folder not found: {MANGA_ROOT}{RESET}")
    print("Set MANGA_ROOT in the .env file (or create a 'manga' folder) and try again.")
    sys.exit(1)

  try:
    while True:
      mode = forced or ask_mode()
      if mode is None:
        break
      if mode == "read":
        run_read_mode(MANGA_ROOT)
      elif mode == "download":
        run_download_mode(MANGA_ROOT)
      else:
        run_manager()
      if forced:       # started with an argument: stop when that part is done
        break
  except (KeyboardInterrupt, EOFError):
    pass

  clear_screen()
  print("Goodbye!")


if __name__ == "__main__":
  main()
