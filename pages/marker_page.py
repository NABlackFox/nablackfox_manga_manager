from utils import (
    BOLD, CYAN, RED, RESET, list_subfolders
)
import functions.chapter_marker as chapter_marker
import helpers.merged_folder as merged_folder
from helpers.prompts import (
    ask_single_folder, ask_number, message_screen, read_confirm, pause
)
from helpers.screens import show_chapters

TITLE = "Edit chapter marker"

def run_markers(author, manga_root):
  folders = merged_folder.list_merged_folders(list_subfolders(manga_root / author))
  if not folders:
    message_screen(
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
  count = merged_folder.merged_chapter_count(folder)

  while True:
    pages, markers = merged_folder.read_pages(folder)

    def parse_chapter(text):
      if not text.isdigit() or not 1 <= int(text) <= count:
        raise ValueError(f"Enter a chapter from 1 to {count}.")
      return int(text)

    chapter = ask_number(
        "  Chapter > ",
        lambda err: show_chapters(
            author, folder, count, markers, manga_root, TITLE,
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
            author, folder, count, markers, manga_root, TITLE,
            f"Chapter {chapter}: enter the page number where it now starts.", err),
        parse_start,
    )
    if start is None:
      continue

    renames = chapter_marker.plan_marker(chapter, start, pages, markers)
    if not renames:
      message_screen(
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