import ctypes
import os
import re
import shutil
import unicodedata
from pathlib import Path

# Terminal colors (ANSI)
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
GREEN = "\033[32m"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


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


def natural_key(path_or_str):
  """Sort key that orders names by the numbers inside them (2 before 10)."""
  name = path_or_str.name if isinstance(path_or_str, Path) else str(path_or_str)
  return [
      int(part) if part.isdigit() else part.lower()
      for part in re.split(r"(\d+)", name)
  ]


def list_subfolders(folder):
  """Return the sub folders of a folder (hidden ones skipped), sorted naturally."""
  try:
    folders = [
        f for f in folder.iterdir() if f.is_dir() and not f.name.startswith(".")
    ]
  except OSError:
    return []
  folders.sort(key=natural_key)
  return folders


def list_images(folder):
  """Return the image files in a folder, sorted by the number in the name."""
  try:
    images = [
        f
        for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]
  except OSError:
    return []
  images.sort(key=natural_key)
  return images


def is_inside(child, parent):
  """True if child is the same as parent or located somewhere inside it."""
  try:
    child, parent = child.resolve(), parent.resolve()
    return child == parent or parent in child.parents
  except Exception:
    return False


def print_header(manga_root, subtitle=""):
  """Print the title banner at the top of every screen."""
  width = min(shutil.get_terminal_size().columns, 80)
  line = "=" * width
  print(f"{CYAN}{line}{RESET}")
  print(f"{BOLD}{CYAN}  MANGA LIBRARY MANAGER{RESET}")
  if subtitle:
    print(f"{DIM}  {subtitle}{RESET}")
  print(f"{CYAN}{line}{RESET}\n")


def print_title(title, author):
  """Print the function title and the author name under the banner."""
  print(f"  {BOLD}{title}{RESET} {DIM}-{RESET} {GREEN}{author}{RESET}\n")


def group_key(name):
  """Letter heading for an author: 'A'-'Z', or '#' for numbers and symbols."""
  first = unicodedata.normalize("NFD", name[:1])[:1]
  return first.upper() if first.isalpha() else "#"


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

# A merged page is "001.png" or, for the first page of a chapter, "001-chapter2.png"
PAGE_RE = re.compile(r"^(\d+)(?:-chapter(\d+))?$", re.IGNORECASE)


def parse_page(file):
  """Return (page number, chapter number or None) for a merged page, else None."""
  match = PAGE_RE.match(file.stem)
  if not match:
    return None
  chapter = int(match.group(2)) if match.group(2) else None
  return int(match.group(1)), chapter


def page_name(number, width, suffix, chapter=None):
  """Build a page file name, e.g. 007.png or 007-chapter2.png."""
  marker = f"-chapter{chapter}" if chapter else ""
  return f"{number:0{width}d}{marker}{suffix}"