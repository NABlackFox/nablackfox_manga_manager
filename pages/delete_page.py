from utils import (
    BOLD, CYAN, DIM, GREEN, RED, YELLOW, RESET,
    clear_screen, print_header, print_title, list_subfolders,
    list_images, parse_page, natural_key, parse_selection,
)
from helpers.prompts import (
    ask_single_folder, read_text, read_confirm, message_screen, pause,
)
import functions.delete_pages as delete_pages
import helpers.merged_folder as merged_folder

TITLE = "Delete pages"


def run_delete_pages(author, manga_root):
  author_folder = manga_root / author
  folders = [
      folder for folder in list_subfolders(author_folder)
      if any(parse_page(image) for image in list_images(folder))
  ]
  if not folders:
    message_screen(author, ["No folders with numbered page images were found."], manga_root, TITLE)
    return

  folder = ask_single_folder(
      author, folders, TITLE,
      "Choose the manga folder to delete pages from.", manga_root
  )
  if folder is None:
    return

  error = ""
  while True:
    numbered = []
    for file in list_images(folder):
      parsed = parse_page(file)
      if parsed:
        numbered.append((parsed[0], file, parsed[1]))
    numbered.sort(key=lambda item: (item[0], natural_key(item[1].name)))

    page_numbers = sorted({number for number, _file, _chapter in numbered})
    if not page_numbers:
      message_screen(author, ["No numbered page images remain in this folder."], manga_root, TITLE)
      return

    clear_screen()
    print_header(manga_root, f"Library: {manga_root}")
    print_title(TITLE, author)
    print(f"  {GREEN}{folder.name}{RESET}\n")
    print(f"  {BOLD}Pages (select the list numbers on the left){RESET}\n")

    for index, page_number in enumerate(page_numbers, start=1):
      files = [
          file.name for number, file, _chapter in numbered
          if number == page_number
      ]
      marker = next(
          (
              chapter for number, _file, chapter in numbered
              if number == page_number and chapter
          ),
          None,
      )
      marker_text = f" {DIM}[chapter {marker} marker]{RESET}" if marker else ""
      print(
          f"  {YELLOW}{index:>3}{RESET}  Page {page_number}: "
          f"{', '.join(files)}{marker_text}"
      )

    print(
        f"\n  {DIM}Enter list numbers like 3, 8 9, or 2-5. "
        "You can combine them with commas. Esc to cancel.{RESET}\n"
    )
    if error:
      print(f"  {RED}{error}{RESET}\n")
      error = ""

    text = read_text("  Pages to delete > ")
    if text is None:
      return

    try:
      indexes = parse_selection(text, len(page_numbers))
      if not indexes:
        raise ValueError("Select at least one page.")
      selected = sorted({page_numbers[index - 1] for index in indexes})
    except ValueError as exc:
      error = str(exc)
      continue
    break

  print(f"\n  {RED}{BOLD}WARNING 1/3: PAGE DELETION{RESET}")
  print(f"  {RED}Selected page numbers: {', '.join(map(str, selected))}{RESET}")
  print(f"  {RED}These image files will be moved to the recycle bin.{RESET}\n")
  if not read_confirm("  Confirm deletion? (y/n) "):
    print("\n  Cancelled. Nothing was changed.\n")
    pause()
    return

  print(f"\n  {RED}{BOLD}WARNING 2/3: RENUMBERING{RESET}")
  print(f"  {RED}Folder: {folder.name}{RESET}")
  print(f"  {RED}All remaining numbered pages will be renumbered from 001.{RESET}")
  print(f"  {RED}Chapter markers may move to the first surviving page of their chapter.{RESET}\n")
  if not read_confirm("  Are you absolutely sure? (y/n) "):
    print("\n  Cancelled. Nothing was changed.\n")
    pause()
    return

  print(f"\n  {RED}{BOLD}WARNING 3/3: FINAL CONFIRMATION{RESET}")
  print(f"  {RED}This changes filenames and sends selected pages to the recycle bin.{RESET}")
  print(f"  {RED}Review your selection before continuing.{RESET}\n")
  if not read_confirm("  Delete these pages now? (y/n) "):
    print("\n  Cancelled. Nothing was changed.\n")
    pause()
    return

  try:
    deleted, remaining, recycle_error = delete_pages.delete_and_renumber(
        folder, selected
    )
  except Exception as exc:
    print(f"\n  {RED}Deletion/renumbering failed: {exc}{RESET}")
    print(
        "  The operation attempted to restore the original filenames. "
        "Check the folder before retrying.\n"
    )
    pause()
    return

  print(
      f"\n  {GREEN}Done! Removed {deleted} image file(s) across "
      f"{len(selected)} selected page number(s).{RESET}"
  )
  print(
      f"  {GREEN}{remaining} numbered page image(s) remain; "
      f"numbering has been compacted.{RESET}"
  )

  if recycle_error:
    print(
        f"  {RED}The selected pages could not be sent to the recycle bin: "
        f"{recycle_error}{RESET}"
    )
    print(
        f"  {RED}They are still in the hidden folder: "
        f"{folder / delete_pages.STAGING_NAME}{RESET}"
    )

  if merged_folder.merged_chapter_count(folder):
    print(
        f"  {DIM}This is a merged folder. Chapter markers were kept on "
        "the first surviving page of each chapter where possible.{RESET}"
    )
    print(
        f"  {YELLOW}If an entire chapter was deleted, review the folder's "
        f"Chapters 1-X name and markers afterward.{RESET}"
    )

  print()
  pause()