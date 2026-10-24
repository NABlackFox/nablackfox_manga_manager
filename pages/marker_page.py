from utils import (
    BOLD, CYAN, DIM, GREEN, RED, YELLOW, RESET,
    clear_screen, print_header, print_title, list_subfolders
)
import functions.chapter_marker as chapter_marker
from pages.merge_page import merge_message_screen, read_text, read_confirm
from pages.append_page import ask_single_folder, pause

TITLE = "Edit chapter marker"

def show_chapters(author, folder, count, markers, manga_root, prompt_text, error=""):
  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(TITLE, author)
  print(f"  {GREEN}{folder.name}{RESET}\n")
  digits = len(str(count))
  for chapter in range(1, count + 1):
    entries = markers.get(chapter)
    if entries:
      number, file = entries[0]
      print(f"  {YELLOW}{chapter:>{digits}}{RESET}  starts at page {number}  {DIM}({file.name}){RESET}")
    else:
      print(f"  {YELLOW}{chapter:>{digits}}{RESET}  {DIM}no marker{RESET}")
  print(f"\n  {DIM}{prompt_text}  Esc to go back.{RESET}\n")
  if error:
    print(f"  {RED}{error}{RESET}\n")

def ask_number(question, show, parse):
  """Ask until `parse` accepts the text; None when cancelled with Esc."""
  error = ""
  while True:
    show(error)
    text = read_text(question)
    if text is None:
      return None
    try:
      return parse(text.strip())
    except ValueError as exc:
      error = str(exc)

def run_markers(author, manga_root):
  folders = chapter_marker.list_merged_folders(list_subfolders(manga_root / author))
  if not folders:
    merge_message_screen(
        author, ["No merged folder (name ending in 'Chapters 1-X') found."],
        manga_root, TITLE,
    )
    return

  folder = ask_single_folder(
      author, folders, TITLE,
      "Enter the number of the merged manga folder.", manga_root
  )
  if folder is None:
    return
  count = chapter_marker.merged_chapter_count(folder)

  while True:
    pages, markers = chapter_marker.read_pages(folder)

    def parse_chapter(text):
      if not text.isdigit() or not 1 <= int(text) <= count:
        raise ValueError(f"Enter a chapter from 1 to {count}.")
      return int(text)

    chapter = ask_number(
        "  Chapter > ",
        lambda err: show_chapters(
            author, folder, count, markers, manga_root,
            "Enter the chapter whose marker you want to change.", err),
        parse_chapter,
    )
    if chapter is None:
      return

    def parse_start(text):
      if not text.isdigit():
        raise ValueError("Enter a page number.")
      start = int(text)
      chapter_marker.check_start(chapter, start, pages, markers)
      return start

    start = ask_number(
        "  Start page > ",
        lambda err: show_chapters(
            author, folder, count, markers, manga_root,
            f"Chapter {chapter}: enter the page number where it now starts.", err),
        parse_start,
    )
    if start is None:
      continue

    renames = chapter_marker.plan_marker(chapter, start, pages, markers)
    if not renames:
      merge_message_screen(
          author, [f"Chapter {chapter} already starts at page {start}. Nothing to change."],
          manga_root, TITLE,
      )
      continue

    print(f"\n  {BOLD}Chapter {chapter} will start at page {start}.{RESET}\n")
    for source, target in renames:
      print(f"  {source.name}  ->  {CYAN}{target.name}{RESET}")
    print()
    if not read_confirm("  Continue? (y/n) "):
      continue

    try:
      chapter_marker.apply_renames(renames)
    except Exception as exc:
      print(f"\n  {RED}Failed: {exc}{RESET}")
      print("  Everything was rolled back.\n")
      pause()