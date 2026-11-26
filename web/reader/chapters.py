"""Start a new chapter from the reader.

This reuses the terminal's marker code on purpose (same file naming, same rename-with-undo), so the web
and the terminal always agree. It only does one thing: start a new chapter on the page you are reading.
Fixing a wrong marker still goes through the terminal. Only page file names change, never the folder name.
"""
from collections import namedtuple

from terminal.shared.utils import list_images, parse_page
from terminal.author_menu.chapter_marker.chapter_marker import apply_renames, with_marker
from terminal.author_menu.shared.merged_folder import read_pages

Plan = namedtuple("Plan", "renames lines")


class MarkError(Exception):
  """Something the reader can understand: shown to the user as it is."""


def plan_new_chapter(folder, index):
  """Work out the renames for 'a new chapter starts on page index+1'. Raises MarkError if it should not be done.

  - no chapter markers yet: the first page becomes Chapter 1 and this page Chapter 2
    (only Chapter 1 when you are on the first page itself)
  - markers exist: this page becomes the last chapter number + 1, and only if it comes after that chapter's start
  """
  files = list_images(folder)
  if not 0 <= index < len(files):
    raise MarkError("That page does not exist.")
  pages, markers = read_pages(folder)
  here = files[index]
  parsed = parse_page(here)
  if parsed is None:
    raise MarkError("This page is not numbered like 001.png, so it cannot hold a chapter marker.")
  number, chapter_here = parsed
  if len(pages[number]) > 1:
    raise MarkError(f"Page {number} exists more than once (different extensions). Fix it in the terminal first.")
  if chapter_here:
    raise MarkError(f"Chapter {chapter_here} already starts on this page.")

  position = lambda file: files.index(file) + 1     # the page numbers the reader shows
  renames, lines = [], []

  if not markers:
    first_number = min(pages)
    first = pages[first_number][0]
    if len(pages[first_number]) > 1:
      raise MarkError(f"Page {first_number} exists more than once (different extensions). Fix it in the terminal first.")
    if first != here:
      renames.append((first, with_marker(first, 1)))
      lines.append(f"Page {position(first)} becomes Chapter 1")
      new_chapter = 2
    else:
      new_chapter = 1
  else:
    last = max(markers)
    if len(markers[last]) > 1:
      raise MarkError(f"Chapter {last} has more than one marker. Fix it in the terminal first.")
    last_start = markers[last][0][0]
    if number <= last_start:
      raise MarkError(
          f"Chapter {last} already starts at page {position(markers[last][0][1])}. "
          "A new chapter can only start after it. Use the terminal to change earlier markers.")
    new_chapter = last + 1

  renames.append((here, with_marker(here, new_chapter)))
  lines.append(f"Page {position(here)} becomes Chapter {new_chapter}")
  return Plan(renames, lines)


def apply(plan):
  try:
    apply_renames(plan.renames)
  except OSError as exc:
    raise MarkError(f"Could not rename the pages ({exc}). Nothing was changed.") from exc
