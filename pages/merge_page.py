from utils import (
    BOLD, CYAN, DIM, GREEN, RED, YELLOW, RESET,
    clear_screen, print_header, print_title, list_subfolders, is_inside
)
import functions.merge_manga as merge_manga
from helpers.prompts import ask_merge_order, message_screen, read_confirm, pause

TITLE = "Merge manga"

def run_merge(author, manga_root):
  author_folder = manga_root / author
  folders = list_subfolders(author_folder)
  if not folders:
    message_screen(author, ["No folders to merge in this author folder."], manga_root, TITLE)
    return

  chosen = ask_merge_order(author, folders, manga_root)
  if chosen is None:
    return

  plan = merge_manga.build_plan(chosen)
  merged_name = (
      merge_manga.build_merged_name(chosen[0].name, len(chosen))
      or "merged_output"
  )
  output_folder = author_folder / merged_name

  if not plan:
    message_screen(author, [f"{RED}No image files found in the selected folders.{RESET}"], manga_root, TITLE)
    return
  if any(is_inside(output_folder, f) for f in chosen):
    message_screen(
        author,
        [f"{RED}The output folder name matches one of the selected folders:{RESET}", merged_name],
        manga_root, TITLE
    )
    return

  pages = {}
  for _file, label in plan:
    pages[label] = pages.get(label, 0) + 1

  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(TITLE, author)
  print(f"  {BOLD}Merge order{RESET}\n")
  digits = len(str(len(chosen)))
  for number, folder in enumerate(chosen, start=1):
    count = pages.get(folder.name, 0)
    print(
        f"  {YELLOW}{number:>{digits}}.{RESET} {CYAN}{folder.name}{RESET}"
        f" {DIM}({count} page{'' if count == 1 else 's'}){RESET}"
    )
  print(f"\n  {BOLD}Output folder{RESET}\n")
  print(f"  {GREEN}{merged_name}{RESET}\n")
  print(f"  {len(plan)} pages in total. After merging, the {len(chosen)} source folder(s)\n  are moved to the recycle bin.")

  if output_folder.exists() and any(output_folder.iterdir()):
    print(f"\n  {RED}The output folder already exists and is not empty. Files with the same names will be overwritten.{RESET}")
  print()

  if not read_confirm("  Continue? (y/n) "):
    print("\n  Cancelled. Nothing was changed.\n")
    pause()
    return

  print()
  try:
    for number, total in merge_manga.copy_pages(plan, output_folder):
      print(f"\r  Copying pages... {number}/{total}", end="", flush=True)
    print()
  except Exception as error:
    print(f"\n\n  {RED}Copy failed: {error}{RESET}")
    print("  The source folders were NOT touched.\n")
    pause()
    return

  copied = len(merge_manga.list_images(output_folder))
  if copied < len(plan):
    print(f"\n  {RED}Warning: expected at least {len(plan)} images in the output folder but found {copied}.{RESET}")
    print("  The source folders were NOT touched.\n")
    pause()
    return

  print()
  for folder, error in merge_manga.recycle_folders(chosen):
    if error is None:
      print(f"  {GREEN}OK{RESET}      {folder.name}")
    else:
      print(f"  {RED}FAILED{RESET}  {folder.name} ({error})")
  print(f"\n  {GREEN}Done!{RESET} {len(plan)} pages merged. The source folders are in the recycle bin\n  if you need them back.")
  print()
  pause()