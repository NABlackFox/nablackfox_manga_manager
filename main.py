import ctypes
import math
import os
import shutil
import sys
from pathlib import Path

from prompt_toolkit import prompt  # pip install prompt_toolkit
from prompt_toolkit.completion import WordCompleter

# Mother folder: contains one folder per author, each holding the manga folders
MANGA_ROOT = Path(r"C:\NABlackFoxDisk\Pic\noncheck")

# Terminal colors (ANSI)
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
GREEN = "\033[32m"

def enable_ansi():
  """Turn on ANSI colors / escape codes in the Windows console."""
  if os.name != "nt":
    return
  try:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)  # standard output
    mode = ctypes.c_ulong()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
      kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # VT processing
  except Exception:
    pass

def clear_screen():
  """Clear the terminal (and its scroll-back) so each screen starts clean."""
  print("\033[2J\033[3J\033[H", end="", flush=True)

def list_folders(parent):
  """Return the sub folder names of a folder, sorted alphabetically."""
  try:
    names = [
        f.name
        for f in parent.iterdir()
        if f.is_dir() and not f.name.startswith(".")
    ]
  except OSError:
    return []
  return sorted(names, key=lambda name: name.casefold())

def print_header(subtitle=""):
  """Print the title banner at the top of every screen."""
  width = min(shutil.get_terminal_size().columns, 80)
  line = "=" * width
  print(f"{CYAN}{line}{RESET}")
  print(f"{BOLD}{CYAN}  MANGA LIBRARY MANAGER{RESET}")
  if subtitle:
    print(f"{DIM}  {subtitle}{RESET}")
  print(f"{CYAN}{line}{RESET}\n")

def print_author_grid(authors):
  """Print the authors in neat columns, alphabetical left to right, top to bottom."""
  term_width = shutil.get_terminal_size().columns
  entries = [
      (name, len(list_folders(MANGA_ROOT / name))) for name in authors
  ]

  labels = [f"{name} ({count})" for name, count in entries]
  col_width = min(max(len(label) for label in labels) + 3, term_width - 4)
  columns = max(1, (term_width - 2) // col_width)
  rows = math.ceil(len(entries) / columns)

  for row in range(rows):
    line = "  "
    for col in range(columns):
      index = row * columns + col
      if index >= len(entries):
        continue
      name, count = entries[index]
      label = f"{name} ({count})"
      if len(label) > col_width - 1:
        # Shorten very long names so columns stay aligned
        name = name[: col_width - 6 - len(str(count))] + "..."
        label = f"{name} ({count})"
      padding = " " * (col_width - len(label))
      line += f"{YELLOW}{name}{RESET} {DIM}({count}){RESET}{padding}"
    print(line.rstrip())

def show_main_menu(authors, error=""):
  """Draw the main menu: all authors plus the instructions."""
  clear_screen()
  print_header(f"Library: {MANGA_ROOT}")
  print(f"  {BOLD}Authors{RESET} {DIM}({len(authors)}){RESET}\n")
  print_author_grid(authors)
  print()
  print(
      f"  {DIM}Type an author name (Tab to auto-complete)."
      f"  Ctrl+C to exit.{RESET}\n"
  )
  if error:
    print(f"  {RED}{error}{RESET}\n")

def ask_for_author(authors):
  """Ask for an author name with Tab auto-complete. Returns the real folder name."""
  lookup = {name.lower(): name for name in authors}
  completer = WordCompleter(
      authors, ignore_case=True, match_middle=True, sentence=True
  )

  error = ""
  while True:
    show_main_menu(authors, error)
    text = prompt("  Author > ", completer=completer).strip().strip('"\'')
    if not text:
      error = ""
      continue
    if text.lower() in lookup:
      return lookup[text.lower()]
    error = f'No author folder named "{text}". Try again.'

def author_menu(author):
  """Temporary submenu: only shows the chosen author for now."""
  clear_screen()
  print_header(f"Library: {MANGA_ROOT}")
  print(f"  {BOLD}Author:{RESET} {GREEN}{author}{RESET}\n")
  print(f"  {DIM}(Functions will be added here later.){RESET}\n")
  input(f"  {DIM}Press Enter to go back to the main menu...{RESET}")

def main():
  enable_ansi()

  if not MANGA_ROOT.is_dir():
    print(f"{RED}Library folder not found: {MANGA_ROOT}{RESET}")
    print("Edit MANGA_ROOT at the top of main.py and try again.")
    sys.exit(1)

  try:
    while True:
      authors = list_folders(MANGA_ROOT)  # re-read so new folders show up
      if not authors:
        clear_screen()
        print_header(f"Library: {MANGA_ROOT}")
        print(f"  {RED}No author folders found in the library.{RESET}\n")
        return
      author = ask_for_author(authors)
      author_menu(author)
  except (KeyboardInterrupt, EOFError):
    pass

  clear_screen()
  print("Goodbye!")

if __name__ == "__main__":
  main()