import math
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from utils import (
    BOLD, CYAN, DIM, GREEN, RED, YELLOW, RESET,
    clear_screen, print_header, group_key, natural_key
)
from pages.unzip_page import run_unzip
from pages.merge_page import run_merge
from pages.append_page import run_append

FUNCTIONS = {
    "1": "Unzip manga",
    "2": "Merge manga",
    "3": "Append chapters",
    "4": "Refresh",
}

def list_folders_sorted(parent):
  try:
    names = [f.name for f in parent.iterdir() if f.is_dir() and not f.name.startswith(".")]
  except OSError:
    return []
  return sorted(names, key=lambda name: name.casefold())

def list_entries(folder):
  try:
    entries = [f for f in folder.iterdir() if not f.name.startswith(".")]
  except OSError:
    return []
  return sorted(entries, key=lambda f: natural_key(f.name))

def print_overview(folder):
  entries = list_entries(folder)
  folder_count = sum(1 for e in entries if e.is_dir())
  zip_count = sum(1 for e in entries if e.is_file() and e.suffix.lower() == ".zip")

  print(f"  {BOLD}Contents{RESET} {DIM}({folder_count} folders, {zip_count} zips){RESET}\n")
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

def print_rows(entries, columns, col_width, manga_root):
  rows = math.ceil(len(entries) / columns)
  for row in range(rows):
    line = "    "
    for col in range(columns):
      index = row * columns + col
      if index >= len(entries):
        continue
      name, count = entries[index]
      label = f"{name} ({count})"
      if len(label) > col_width - 1:
        name = name[: col_width - 6 - len(str(count))] + "..."
        label = f"{name} ({count})"
      padding = " " * (col_width - len(label))
      line += f"{YELLOW}{name}{RESET} {DIM}({count}){RESET}{padding}"
    print(line.rstrip())

def print_author_grid(authors, manga_root):
  import shutil
  term_width = shutil.get_terminal_size().columns
  entries = [(name, len(list_folders_sorted(manga_root / name))) for name in authors]

  labels = [f"{name} ({count})" for name, count in entries]
  col_width = min(max(len(label) for label in labels) + 3, term_width - 4)
  columns = max(1, (term_width - 4) // col_width)

  groups = {}
  for entry in entries:
    groups.setdefault(group_key(entry[0]), []).append(entry)

  for key in sorted(groups, key=lambda k: (k != "#", k)):
    print(f"  {BOLD}{CYAN}{key}{RESET}")
    print_rows(groups[key], columns, col_width, manga_root)
    print()

def show_main_menu(authors, manga_root, error=""):
  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print(f"  {BOLD}Authors{RESET} {DIM}({len(authors)}){RESET}\n")
  print_author_grid(authors, manga_root)
  print()
  print(f"  {DIM}Type an author name (Tab to auto-complete).  Enter on an empty line to refresh.  Ctrl+C to exit.{RESET}\n")
  if error:
    print(f"  {RED}{error}{RESET}\n")

def ask_for_author(manga_root):
  error = ""
  while True:
    authors = list_folders_sorted(manga_root)
    if not authors:
      return None
    lookup = {name.lower(): name for name in authors}
    completer = WordCompleter(authors, ignore_case=True, match_middle=True, sentence=True)

    show_main_menu(authors, manga_root, error)
    text = prompt("  Author > ", completer=completer).strip().strip('"\'')
    if not text:
      error = ""
      continue

    # Open admin menu when the user types "admin"
    if text.casefold() == "admin":
      return "admin"

    if text.lower() in lookup:
      return lookup[text.lower()]
    error = f'No author folder named "{text}". Try again.'

def read_choice():
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

def run_author_menu(author, manga_root):
  message = ""
  while True:
    if not (manga_root / author).is_dir():
      return
    clear_screen()
    print_header(manga_root, f"Library: {manga_root}")
    print(f"  {BOLD}Author:{RESET} {GREEN}{author}{RESET}\n")
    print_overview(manga_root / author)

    print(f"  {BOLD}Functions{RESET}\n")
    for key, name in FUNCTIONS.items():
      print(f"  {YELLOW}{key}{RESET}  {name}")
    print(f"\n  {DIM}Press 1-{len(FUNCTIONS)} to choose, Esc to go back, Ctrl+C to exit.{RESET}\n")
    if message:
      print(f"  {GREEN}{message}{RESET}\n")

    choice = read_choice()
    if choice == "esc":
      return
    if not (manga_root / author).is_dir():
      return

    runners = {
        "1": lambda a: run_unzip(a, manga_root),
        "2": lambda a: run_merge(a, manga_root),
        "3": lambda a: run_append(a, manga_root),
    }
    if choice in runners:
      runners[choice](author)
      message = ""
    else:
      message = "Refreshed."