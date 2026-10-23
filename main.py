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

import merge_manga  # same folder as this file
import unzip_manga

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

def read_text(question):
  """Read one line of text. Enter submits it; Esc cancels and returns None."""
  kb = KeyBindings()

  @kb.add("escape", eager=True)
  def _cancel(event):
    event.app.exit(result=None)

  return prompt(question, key_bindings=kb)

def parse_selection(text, count):
  """Turn '2', '1 3 5' or '4-7' into a list of numbers (ValueError if invalid)."""
  numbers = []
  for token in re.split(r"[,\s]+", text.strip()):
    if not token:
      continue
    match = re.fullmatch(r"(\d+)(?:-(\d+))?", token)
    if not match:
      raise ValueError(f'"{token}" is not a number from the list.')
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if start > end:
      raise ValueError(f'"{token}" is not a valid range.')
    if start < 1 or end > count:
      raise ValueError(f"{token} is out of range (the list has 1-{count}).")
    numbers.extend(range(start, end + 1))
  return numbers

def show_merge_screen(author, folders, chosen, error=""):
  """Numbered folder list, the order picked so far, and the instructions."""
  clear_screen()
  print_header(f"Library: {MANGA_ROOT}")
  print(f"  {BOLD}Merge manga{RESET} {DIM}-{RESET} {GREEN}{author}{RESET}\n")

  digits = len(str(len(folders)))
  for number, folder in enumerate(folders, start=1):
    if folder in chosen:
      print(f"  {DIM}{number:>{digits}}  {folder.name}{RESET}")
    else:
      print(f"  {YELLOW}{number:>{digits}}{RESET}  {CYAN}{folder.name}{RESET}")
  print()

  if chosen:
    print(f"  {BOLD}Merge order so far{RESET}\n")
    for folder in chosen:
      print(f"  {folder.name}")
    print()

  print(
      f"  {DIM}Enter the number of each folder in the order it should be merged"
      f" (e.g. 3, or 1 4 2, or 5-9).{RESET}"
  )
  print(
      f"  {DIM}Press Enter on an empty line when you are done."
      f"  Esc to cancel.{RESET}\n"
  )
  if error:
    print(f"  {RED}{error}{RESET}\n")

def ask_merge_order(author, folders):
  """Ask for the folders by number, in merge order. None means cancelled."""
  chosen = []
  error = ""
  while True:
    show_merge_screen(author, folders, chosen, error)
    error = ""
    text = read_text(f"  Folder {len(chosen) + 1} > ")
    if text is None:
      return None

    if not text.strip():
      if not chosen:
        error = "Pick at least one folder first."
        continue
      return chosen

    try:
      numbers = parse_selection(text, len(folders))
    except ValueError as exc:
      error = str(exc)
      continue

    already = []
    for number in numbers:
      folder = folders[number - 1]
      if folder in chosen:
        already.append(str(number))
      else:
        chosen.append(folder)
    if already:
      error = f"Already added, skipped: {', '.join(already)}"

def merge_message_screen(author, lines):
  """Show a short message under the Merge title and wait for Enter."""
  clear_screen()
  print_header(f"Library: {MANGA_ROOT}")
  print(f"  {BOLD}Merge manga{RESET} {DIM}-{RESET} {GREEN}{author}{RESET}\n")
  for line in lines:
    print(f"  {line}")
  print()
  input(f"  {DIM}Press Enter to go back...{RESET}")

def run_merge(author):
  """Function 2: merge chosen chapter folders into one numbered folder."""
  author_folder = MANGA_ROOT / author
  folders = merge_manga.list_subfolders(author_folder)
  if not folders:
    merge_message_screen(author, ["No folders to merge in this author folder."])
    return

  # 1. Pick the folders by number, in merge order
  chosen = ask_merge_order(author, folders)
  if chosen is None:
    return

  # 2. Work out what will happen
  plan = merge_manga.build_plan(chosen)
  merged_name = (
      merge_manga.build_merged_name(chosen[0].name, len(chosen))
      or "merged_output"
  )
  output_folder = author_folder / merged_name

  if not plan:
    merge_message_screen(
        author, [f"{RED}No image files found in the selected folders.{RESET}"]
    )
    return
  if any(merge_manga.is_inside(output_folder, f) for f in chosen):
    merge_message_screen(
        author,
        [
            f"{RED}The output folder name matches one of the selected"
            f" folders:{RESET}",
            merged_name,
        ],
    )
    return

  # 3. Show the result and ask to continue
  pages = {}
  for _file, label in plan:
    pages[label] = pages.get(label, 0) + 1

  clear_screen()
  print_header(f"Library: {MANGA_ROOT}")
  print(f"  {BOLD}Merge manga{RESET} {DIM}-{RESET} {GREEN}{author}{RESET}\n")
  print(f"  {BOLD}Merge order{RESET}\n")
  for folder in chosen:
    count = pages.get(folder.name, 0)
    print(f"  {CYAN}{folder.name}{RESET} {DIM}({count} pages){RESET}")
  print(f"\n  {BOLD}Output folder{RESET}\n")
  print(f"  {GREEN}{merged_name}{RESET}\n")
  print(
      f"  {len(plan)} pages in total. After merging, the {len(chosen)} source"
      " folder(s)\n  are moved to the recycle bin."
  )
  if output_folder.exists() and any(output_folder.iterdir()):
    print(
        f"\n  {RED}The output folder already exists and is not empty."
        f" Files with the same names will be overwritten.{RESET}"
    )
  print()

  if not read_confirm("  Continue? (y/n) "):
    print("\n  Cancelled. Nothing was changed.\n")
    input(f"  {DIM}Press Enter to go back...{RESET}")
    return

  # 4. Copy the pages
  print()
  try:
    for number, total in merge_manga.copy_pages(plan, output_folder):
      print(f"\r  Copying pages... {number}/{total}", end="", flush=True)
    print()
  except Exception as error:
    print(f"\n\n  {RED}Copy failed: {error}{RESET}")
    print("  The source folders were NOT touched.\n")
    input(f"  {DIM}Press Enter to go back...{RESET}")
    return

  # 5. Only after every page was copied, send the source folders to the bin
  copied = len(merge_manga.list_images(output_folder))
  if copied < len(plan):
    print(
        f"\n  {RED}Warning: expected at least {len(plan)} images in the"
        f" output folder but found {copied}.{RESET}"
    )
    print("  The source folders were NOT touched.\n")
    input(f"  {DIM}Press Enter to go back...{RESET}")
    return

  print()
  for folder, error in merge_manga.recycle_folders(chosen):
    if error is None:
      print(f"  {GREEN}OK{RESET}      {folder.name}")
    else:
      print(f"  {RED}FAILED{RESET}  {folder.name} ({error})")
  print(
      f"\n  {GREEN}Done!{RESET} {len(plan)} pages merged. The source folders"
      " are in the recycle bin\n  if you need them back."
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
    if choice in ("1", "2"):
      (run_unzip if choice == "1" else run_merge)(author)
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