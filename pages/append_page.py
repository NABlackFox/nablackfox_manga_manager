from utils import (
    BOLD, CYAN, DIM, GREEN, RED, YELLOW, RESET,
    clear_screen, print_header, print_title, parse_selection, list_subfolders
)
import functions.merge_manga as merge_manga
import functions.manga_chapter_appender as manga_chapter_appender
from pages.merge_page import ask_merge_order, merge_message_screen, read_text, read_confirm

def pause():
  input(f"  {DIM}Press Enter to go back...{RESET}")

def ask_single_folder(author, folders, title, question, manga_root):
  error = ""
  while True:
    clear_screen()
    print_header(manga_root, f"Library: {manga_root}")
    print_title(title, author)
    digits = len(str(len(folders)))
    for number, folder in enumerate(folders, start=1):
      print(f"  {YELLOW}{number:>{digits}}{RESET}  {CYAN}{folder.name}{RESET}")
    print(f"\n  {DIM}{question}  Esc to cancel.{RESET}\n")
    if error:
      print(f"  {RED}{error}{RESET}\n")
      error = ""

    text = read_text("  Folder > ")
    if text is None:
      return None
    try:
      numbers = parse_selection(text, len(folders))
    except ValueError as exc:
      error = str(exc)
      continue
    if len(numbers) != 1:
      error = "Enter exactly one number."
      continue
    return folders[numbers[0] - 1]

def run_append(author, manga_root):
  title = "Append chapters"
  author_folder = manga_root / author
  folders = list_subfolders(author_folder)
  if len(folders) < 2:
    merge_message_screen(
        author,
        ["You need the merged folder and at least one new chapter folder."],
        manga_root,
        title,
    )
    return

  merged_folder = ask_single_folder(
      author, folders, title,
      "Enter the number of the already merged manga folder.",
      manga_root
  )
  if merged_folder is None:
    return

  candidates = [f for f in folders if f != merged_folder]
  chosen = ask_merge_order(
      author, candidates, manga_root, title=title, verb="added",
      note=f"Appending to: {GREEN}{merged_folder.name}{RESET}",
  )
  if chosen is None:
    return

  info = manga_chapter_appender.scan_merged_folder(merged_folder)
  first_chapter = manga_chapter_appender.chapter_count(merged_folder, info) + 1
  plan = merge_manga.build_plan(chosen)
  if not plan:
    merge_message_screen(
        author,
        [f"{RED}No image files found in the selected folders.{RESET}"],
        manga_root,
        title,
    )
    return

  first_new, final_number, width, needs_repad = (
      manga_chapter_appender.numbering(info, len(plan))
  )

  renamed_folder = manga_chapter_appender.build_updated_folder(
      merged_folder, len(chosen)
  )
  rename_note = ""
  if renamed_folder is None:
    rename_note = "The folder name does not end with 'Chapters 1-N', so it will not be renamed."
  elif renamed_folder.exists():
    rename_note = f"{renamed_folder.name} already exists, so the folder will not be renamed."
    renamed_folder = None

  pages = {}
  for _file, label in plan:
    pages[label] = pages.get(label, 0) + 1

  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(title, author)
  print(f"  {BOLD}Appending to{RESET}\n")
  print(f"  {GREEN}{merged_folder.name}{RESET}")
  if info.existing:
    print(f"  {DIM}({len(info.existing)} pages, last page {info.last_number}){RESET}")
  else:
    print(f"  {DIM}(no numbered pages yet, starting from 1){RESET}")
  if info.ignored:
    print(f"  {DIM}{info.ignored} image(s) with non-numeric names are ignored.{RESET}")

  print(f"\n  {BOLD}Chapters to add{RESET}\n")
  digits = len(str(len(chosen)))
  for number, folder in enumerate(chosen, start=1):
    count = pages.get(folder.name, 0)
    print(
        f"  {YELLOW}{number:>{digits}}.{RESET} {CYAN}{folder.name}{RESET}"
        f" {DIM}({count} page{'' if count == 1 else 's'}){RESET}"
    )
  print(f"\n  {len(plan)} new pages will be added as {first_new:0{width}d} to {final_number:0{width}d}.")

  if renamed_folder is not None:
    print(f"\n  {BOLD}New folder name{RESET}\n")
    print(f"  {GREEN}{renamed_folder.name}{RESET}")
  elif rename_note:
    print(f"\n  {YELLOW}{rename_note}{RESET}")

  if needs_repad:
    print(f"\n  {YELLOW}The page count now needs {width} digits, so the {len(info.existing)} existing pages will be renamed to {width} digits.{RESET}")
  print(f"\n  After adding, the {len(chosen)} new chapter folder(s) are moved to the recycle bin.\n")

  if not read_confirm("  Continue? (y/n) "):
    print("\n  Cancelled. Nothing was changed.\n")
    pause()
    return

  print()
  try:
    if needs_repad:
      manga_chapter_appender.repad_existing(info, width)
    for number, total in manga_chapter_appender.copy_pages(
        plan, merged_folder, first_new, width, first_chapter
    ):
      print(f"\r  Copying pages... {number}/{total}", end="", flush=True)
    print()
  except Exception as error:
    print(f"\n\n  {RED}Failed: {error}{RESET}")
    print("  The new chapter folders were NOT touched.\n")
    pause()
    return

  expected = len(info.all_images) + len(plan)
  copied = len(merge_manga.list_images(merged_folder))
  if copied < expected:
    print(f"\n  {RED}Warning: expected at least {expected} images in the merged folder but found {copied}.{RESET}")
    print("  The new chapter folders were NOT touched.\n")
    pause()
    return

  print()
  if renamed_folder is not None:
    try:
      merged_folder.rename(renamed_folder)
      print(f"  {GREEN}Renamed{RESET}  {renamed_folder.name}\n")
    except Exception as error:
      print(f"  {RED}Could not rename the merged folder ({error}){RESET}\n")

  for folder, error in merge_manga.recycle_folders(chosen):
    if error is None:
      print(f"  {GREEN}OK{RESET}      {folder.name}")
    else:
      print(f"  {RED}FAILED{RESET}  {folder.name} ({error})")
  print(f"\n  {GREEN}Done!{RESET} {len(plan)} pages added. The new chapter folders are in the recycle bin.\n")
  pause()