from utils import (
    BOLD, CYAN, DIM, GREEN, RED, YELLOW, RESET,
    clear_screen, print_header, print_title, list_subfolders,
    list_images, parse_page, natural_key, parse_selection,
)
from helpers.prompts import (
    ask_single_folder, ask_merge_order, read_confirm, message_screen, pause,
)
import functions.delete_pages as delete_pages
import helpers.merged_folder as merged_folder

TITLE = "Delete pages"


class PageRow:
  """A page in the picker list: .name is what is shown."""

  def __init__(self, number, name):
    self.number = number
    self.name = name

  def __eq__(self, other):
    return isinstance(other, PageRow) and self.number == other.number

  def __hash__(self):
    return hash(self.number)


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

  # One row per page number, shown with the same picker the merge screen uses.
  rows = []
  for page_number in page_numbers:
    files = [f.name for number, f, _c in numbered if number == page_number]
    marker = next(
        (c for number, _f, c in numbered if number == page_number and c),
        None,
    )
    label = f"Page {page_number}: {', '.join(files)}"
    if marker:
      label += f"  [chapter {marker} marker]"
    rows.append(PageRow(page_number, label))

  picked = ask_merge_order(
      author, rows, manga_root, prompt_label="Page",
      title=TITLE, verb="deleted", noun="page", ordered=False, chosen_label="Pages to delete",
      note=f"Deleting from: {GREEN}{folder.name}{RESET}",
  )
  if picked is None:
    return
  selected = sorted({row.number for row in picked})

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