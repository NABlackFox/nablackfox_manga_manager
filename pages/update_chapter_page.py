from utils import (
    BOLD, CYAN, DIM, GREEN, RED, RESET,
    clear_screen, print_header, print_title, list_images
)
import functions.update_chapter as update_chapter
from helpers.prompts import ask_single_folder, ask_number, message_screen
from helpers.screens import (
    load_merged_folder, show_chapters, print_shift, print_totals,
    confirm_change, apply_and_finish
)

TITLE = "Update Chapter"

def run_update_chapter(author, manga_root):
  data = load_merged_folder(author, manga_root, TITLE)
  if data is None:
    return
  folder, info = data["folder"], data["info"]
  pages, markers, count = data["pages"], data["markers"], data["count"]

  picked = ask_number(
      "  Chapter > ",
      lambda err: show_chapters(
          author, folder, count, markers, manga_root, TITLE,
          "Enter the chapter you want to replace.", err),
      lambda text: update_chapter.parse_chapter(text, count, pages, markers),
  )
  if picked is None:
    return
  chapter, (start, end) = picked

  new_folder = ask_single_folder(
      author, data["candidates"], TITLE,
      f"Enter the number of the folder with the NEW chapter {chapter}.", manga_root,
      split=data["split"],
  )
  if new_folder is None:
    return

  new_files = list_images(new_folder)
  if not new_files:
    message_screen(
        author, [f"{RED}No image files found in {new_folder.name}.{RESET}"],
        manga_root, TITLE,
    )
    return

  plan = update_chapter.build_update_plan(info, chapter, start, end, new_files)
  w = plan.width
  old_count = end - start + 1

  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(TITLE, author)
  print(f"  {BOLD}In{RESET}  {GREEN}{folder.name}{RESET}\n")
  print(f"  {BOLD}Remove{RESET}  chapter {chapter}: pages {start:0{w}d}-{end:0{w}d} {DIM}({old_count} pages){RESET}")
  print(
      f"  {BOLD}Insert{RESET}  {CYAN}{new_folder.name}{RESET} {DIM}({len(new_files)} pages){RESET}"
      f"\n           as pages {start:0{w}d}-{start + len(new_files) - 1:0{w}d}"
  )
  print_shift(plan, info)
  print_totals(plan, info)
  print(
      f"\n  Afterwards the replaced pages and the folder {new_folder.name}\n"
      f"  are moved to the recycle bin.\n"
  )

  if not confirm_change():
    return
  apply_and_finish(
      folder, plan, info, [new_folder], None,
      f"Chapter {chapter} replaced: {old_count} pages -> {len(new_files)} pages.",
  )