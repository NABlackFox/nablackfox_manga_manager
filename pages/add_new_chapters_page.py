from utils import BOLD, DIM, GREEN, RESET, clear_screen, print_header, print_title
import functions.add_new_chapters as add_new_chapters
import functions.merge_manga as merge_manga
import helpers.merged_folder as merged_folder
from helpers.prompts import ask_merge_order, message_screen
from helpers.screens import (
    load_merged_folder, print_new_chapters, print_totals, print_folder_name,
    confirm_change, apply_and_finish
)

TITLE = "Add New Chapters"

def run_add_new_chapters(author, manga_root):
  data = load_merged_folder(
      author, manga_root, TITLE, allow_empty=True
  )
  if data is None:
    return
  folder, info = data["folder"], data["info"]

  chosen = ask_merge_order(
      author, data["candidates"], manga_root, title=TITLE, verb="added",
      split=data["split"],
      note=f"Adding to: {GREEN}{folder.name}{RESET}",
  )
  if chosen is None:
    return

  file_plan = merge_manga.build_plan(chosen)
  if not file_plan:
    message_screen(
        author, ["No image files found in the selected folders."],
        manga_root, TITLE,
    )
    return

  plan, first_chapter = add_new_chapters.build_add_new_plan(info, folder, file_plan)
  renamed_folder = merged_folder.build_updated_folder(folder, len(chosen))

  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(TITLE, author)
  print(f"  {BOLD}Adding to{RESET}\n")
  print(f"  {GREEN}{folder.name}{RESET}")
  if info.existing:
    print(f"  {DIM}({len(info.existing)} pages, last page {info.last_number}){RESET}")
  else:
    print(f"  {DIM}(no numbered pages yet, starting from 1){RESET}")
  if info.ignored:
    print(f"  {DIM}{info.ignored} image(s) with non-numeric names are ignored.{RESET}")

  print(f"\n  {BOLD}Chapters to add{RESET}\n")
  print_new_chapters(chosen, file_plan, first_chapter, plan)
  print_totals(plan, info)
  print_folder_name(renamed_folder)
  print(f"\n  After adding, the {len(chosen)} new chapter folder(s) are moved to the recycle bin.\n")

  if not confirm_change():
    return
  apply_and_finish(
      folder, plan, info, chosen, renamed_folder,
      f"{len(file_plan)} pages added. The new chapter folders are in the recycle bin.",
  )