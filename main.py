import ctypes
import math
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

from prompt_toolkit import prompt  # pip install prompt_toolkit
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings

import unzip_manga  # same folder as this file

# Mother folder: contains one folder per author, each holding the manga folders
MANGA_ROOT = Path(r"C:\NABlackFoxDisk\Pic\noncheck")

# The three functions offered for an author (key -> label)
FUNCTIONS = {
    "1": "Unzip manga",
    "2": "Merge manga",
    "3": "Append chapters",
}

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

def group_key(name):
  """Letter heading for an author: 'A'-'Z', or '#' for numbers and symbols."""
  first = unicodedata.normalize("NFD", name[:1])[:1]  # strips accents (É -> E)
  return first.upper() if first.isalpha() else "#"

def print_rows(entries, columns, col_width):
  """Print entries in rows, reading left to right."""
  rows = math.ceil(len(entries) / columns)
  for row in range(rows):
    line = "    "  # indented under the letter heading
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

def print_author_grid(authors):
  """Print the authors under a letter heading (A, B, ...), indented below it.

  Names starting with a number or symbol go together under '#'.
  """
  term_width = shutil.get_terminal_size().columns
  entries = [
      (name, len(list_folders(MANGA_ROOT / name))) for name in authors
  ]

  # One column width for every group so everything lines up
  labels = [f"{name} ({count})" for name, count in entries]
  col_width = min(max(len(label) for label in labels) + 3, term_width - 4)
  columns = max(1, (term_width - 4) // col_width)

  groups = {}
  for entry in entries:
    groups.setdefault(group_key(entry[0]), []).append(entry)

  for key in sorted(groups, key=lambda k: (k != "#", k)):  # '#' first
    print(f"  {BOLD}{CYAN}{key}{RESET}")
    print_rows(groups[key], columns, col_width)
    print()

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

def natural_key(name):
  """Sort key that orders names by the numbers inside them (2 before 10)."""
  return [
      int(part) if part.isdigit() else part.lower()
      for part in re.split(r"(\d+)", name)
  ]

def list_entries(folder):
  """Return everything at the first level of a folder (hidden items skipped)."""
  try:
    entries = [f for f in folder.iterdir() if not f.name.startswith(".")]
  except OSError:
    return []
  return sorted(entries, key=lambda f: natural_key(f.name))

def print_overview(folder):
  """Quick overview of a folder, one entry per line like `ls`."""
  entries = list_entries(folder)
  folder_count = sum(1 for e in entries if e.is_dir())
  zip_count = sum(
      1 for e in entries if e.is_file() and e.suffix.lower() == ".zip"
  )

  print(
      f"  {BOLD}Contents{RESET}"
      f" {DIM}({folder_count} folders, {zip_count} zips){RESET}\n"
  )
  if not entries:
    print(f"  {DIM}(empty){RESET}")
  for entry in entries:
    if entry.is_dir():
      print(f"  {CYAN}{entry.name}/{RESET}")
    elif entry.suffix.lower() == ".zip":
      print(f"  {RED}{entry.name}{RESET}")
    else:
      print(f"  {entry.name}")
  print()

def read_choice():
  """Wait for one key: 1-3 picks a function, Esc goes back (no Enter needed)."""
  kb = KeyBindings()

  @kb.add("<any>")
  def _ignore(event):
    pass  # swallow other keys so nothing is typed on screen

  for key in FUNCTIONS:
    @kb.add(key, eager=True)
    def _pick(event, key=key):
      event.app.exit(result=key)

  @kb.add("escape", eager=True)
  def _back(event):
    event.app.exit(result="esc")

  return prompt("  > ", key_bindings=kb)

def read_confirm(question):
  """Ask a yes/no question and wait for one key: y = yes, n or Esc = no."""
  kb = KeyBindings()

  @kb.add("<any>")
  def _ignore(event):
    pass  # swallow other keys so nothing is typed on screen

  for key in ("y", "Y"):
    @kb.add(key, eager=True)
    def _yes(event):
      event.app.exit(result=True)

  for key in ("n", "N", "escape"):
    @kb.add(key, eager=True)
    def _no(event):
      event.app.exit(result=False)

  return prompt(question, key_bindings=kb)

def ask_continue(zips):
  """Show the zips that are ready to be unzipped, then ask to continue."""
  print(f"  {BOLD}Ready to unzip{RESET}\n")
  for zip_file in zips:
    print(f"  {RED}{zip_file.name}{RESET}")
  print(
      f"\n  {DIM}Each zip is deleted after it is unzipped successfully.{RESET}\n"
  )
  return read_confirm("  Continue? (y/n) ")

def run_unzip(author):
  """Function 1: unzip every new zip in the author folder."""
  clear_screen()
  print_header(f"Library: {MANGA_ROOT}")
  print(
      f"  {BOLD}Unzip manga{RESET} {DIM}-{RESET} {GREEN}{author}{RESET}\n"
  )
  folder = MANGA_ROOT / author
  to_unzip, skipped = unzip_manga.find_new_zips(folder)

  print(
      f"  Found {BOLD}{len(to_unzip) + skipped}{RESET} zip(s):"
      f" {GREEN}{len(to_unzip)} new{RESET},"
      f" {DIM}{skipped} already unzipped{RESET}.\n"
  )

  if not to_unzip:
    print("  Nothing to unzip.")
  elif not ask_continue(to_unzip):
    print(f"\n  Cancelled. Nothing was changed.")
  else:
    print()
    failed = []
    for number, zip_file, error in unzip_manga.unzip_zips(folder, to_unzip):
      progress = f"[{number}/{len(to_unzip)}]"
      if error is None:
        print(f"  {progress} {GREEN}OK{RESET}      {zip_file.name}")
      else:
        print(f"  {progress} {RED}FAILED{RESET}  {zip_file.name} ({error})")
        failed.append(zip_file.name)

    if failed:
      print(f"\n  {RED}Finished with {len(failed)} failure(s):{RESET}")
      for name in failed:
        print(f"    - {name}")
      print(f"  {DIM}The failed zips were kept, so you can try again.{RESET}")
    else:
      print(
          f"\n  {GREEN}Done!{RESET} {len(to_unzip)} zip(s) unzipped and deleted."
      )

  print()
  input(f"  {DIM}Press Enter to go back...{RESET}")

def author_menu(author):
  """Author screen: folder overview, the three functions, Esc to go back."""
  message = ""
  while True:
    clear_screen()
    print_header(f"Library: {MANGA_ROOT}")
    print(f"  {BOLD}Author:{RESET} {GREEN}{author}{RESET}\n")
    print_overview(MANGA_ROOT / author)

    print(f"  {BOLD}Functions{RESET}\n")
    for key, name in FUNCTIONS.items():
      print(f"  {YELLOW}{key}{RESET}  {name}")
    print(
        f"\n  {DIM}Press 1-{len(FUNCTIONS)} to choose, Esc to go back,"
        f" Ctrl+C to exit.{RESET}\n"
    )
    if message:
      print(f"  {GREEN}{message}{RESET}\n")

    choice = read_choice()
    if choice == "esc":
      return
    if choice == "1":
      run_unzip(author)
      message = ""
      continue
    message =f"Function chosen: {FUNCTIONS[choice]} (not connected yet)"

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