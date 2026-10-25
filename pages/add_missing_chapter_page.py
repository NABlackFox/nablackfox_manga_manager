from utils import BOLD, GREEN, RESET, clear_screen, print_header, print_title
import functions.add_missing_chapter as add_missing_chapter
import functions.merge_manga as merge_manga
import helpers.merged_folder as merged_folder
from helpers.prompts import ask_merge_order, ask_number, message_screen
from helpers.screens import (
    load_merged_folder, show_chapters, print_new_chapters, print_shift,
    print_totals, print_folder_name, confirm_change, apply_and_finish
)

TITLE = "Add Missing Chapter"

def run_add_missing_chapter(author, manga_root):
  data = load_merged_folder(author, manga_root, TITLE)
  if data is None:
    return
  folder, info = data["folder"], data["info"]
  pages, markers, count = data["pages"], data["markers"], data["count"]

  position = ask_number(
      "  Chapter > ",
      lambda err: show_chapters(
          author, folder, count, markers, manga_root, TITLE,
          f"Enter the number the new chapter gets. Chapters from that number move up "
          f"({count + 1} = add at the end).", err),
      lambda text: add_missing_chapter.parse_position(text, count, pages, markers),
  )
  if position is None:
    return
  first_chapter, start = position

  chosen = ask_merge_order(
      author, data["candidates"], manga_root, title=TITLE, verb="inserted",
      split=data["split"],
      note=f"Inserting into: {GREEN}{folder.name}{RESET} starting as chapter {first_chapter}",
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

  plan = add_missing_chapter.build_add_missing_plan(
      info, first_chapter, start, file_plan, len(chosen)
  )
  renamed_folder = merged_folder.build_updated_folder(folder, len(chosen))

  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(TITLE, author)
  print(f"  {BOLD}In{RESET}  {GREEN}{folder.name}{RESET}\n")
  print_new_chapters(chosen, file_plan, first_chapter, plan)
  print()
  if first_chapter <= count:
    print(
        f"  {BOLD}Chapters{RESET} {first_chapter}-{count} become "
        f"{first_chapter + len(chosen)}-{count + len(chosen)}"
    )
  print_shift(plan, info)
  print_totals(plan, info)
  print_folder_name(renamed_folder)
  print(f"\n  After inserting, the {len(chosen)} new chapter folder(s) are moved to the recycle bin.\n")

  if not confirm_change():
    return
  last_chapter = first_chapter + len(chosen) - 1
  chapters_text = (
      f"chapter {first_chapter}" if len(chosen) == 1
      else f"chapters {first_chapter}-{last_chapter}"
  )
  apply_and_finish(
      folder, plan, info, chosen, renamed_folder,
      f"{len(file_plan)} pages inserted as {chapters_text}.",
  )