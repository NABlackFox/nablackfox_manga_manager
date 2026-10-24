from utils import DIM, YELLOW, RESET, clear_screen, print_header, print_title
from helpers.prompts import read_menu_choice
from pages.add_new_chapters_page import run_add_new_chapters
from pages.add_missing_chapter_page import run_add_missing_chapter
from pages.update_chapter_page import run_update_chapter

# key: (name, description, function)
OPTIONS = {
    "1": ("Add New Chapters", "put new chapters after the last page", run_add_new_chapters),
    "2": ("Add Missing Chapter", "insert a chapter in the middle, the rest shifts", run_add_missing_chapter),
    "3": ("Update Chapter", "replace a chapter with a longer or shorter version", run_update_chapter),
}

def run_edit_merged_menu(author, manga_root):
  while True:
    clear_screen()
    print_header(manga_root, f"Library: {manga_root}")
    print_title("Edit Merged Chapters", author)
    for key, (name, description, _function) in OPTIONS.items():
      print(f"  {YELLOW}{key}{RESET}  {name}  {DIM}- {description}{RESET}")
    print(f"\n  {DIM}Press 1-{len(OPTIONS)} to choose, Esc to go back.{RESET}\n")

    choice = read_menu_choice(OPTIONS)
    if choice == "esc":
      return
    OPTIONS[choice][2](author, manga_root)