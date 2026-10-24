from utils import (
    BOLD, CYAN, DIM, GREEN, RED, YELLOW, RESET,
    clear_screen, print_header, print_title, list_subfolders, list_images
)
import helpers.merged_folder as merged_folder
import helpers.splice as splice
from helpers.prompts import (
    ask_single_folder, message_screen, read_confirm, pause
)

# Things that show something, and the flow every "Edit Merged Chapters" page shares.

def show_chapters(author, folder, count, markers, manga_root, title, prompt_text, error=""):
  """List chapters 1..count with the page each one starts at."""
  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(title, author)
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

def load_merged_folder(author, manga_root, title, merged_only=True, allow_empty=False):
  """Let the user pick a merged folder and read it. None if cancelled.

  merged_only: only offer folders named '... Chapters 1-X'.
  """
  folders = list_subfolders(manga_root / author)
  choices = merged_folder.list_merged_folders(folders) if merged_only else folders
  if not choices or len(folders) < 2:
    if merged_only:
      lines = ["You need a merged folder (name ending in 'Chapters 1-X')",
               "and a folder with the new chapter."]
    else:
      lines = ["You need the merged folder and at least one new chapter folder."]
    message_screen(author, lines, manga_root, title)
    return None

  folder = ask_single_folder(
      author, choices, title,
      "Enter the number of the already merged manga folder.", manga_root
  )
  if folder is None:
    return None

  info = merged_folder.scan_merged_folder(folder)
  if not info.existing and not allow_empty:
    message_screen(
        author, [f"{RED}No numbered pages in that folder.{RESET}"],
        manga_root, title,
    )
    return None

  pages, markers = merged_folder.read_pages(folder)
  return {
      "folder": folder,
      "candidates": [f for f in folders if f != folder],
      "info": info,
      "pages": pages,
      "markers": markers,
      "count": merged_folder.merged_chapter_count(folder),
  }

def print_new_chapters(chosen, file_plan, first_chapter, plan):
  """List the new chapters with their page counts and page ranges."""
  per_folder = {}
  for _file, label in file_plan:
    per_folder[label] = per_folder.get(label, 0) + 1
  w = plan.width
  page = plan.start
  for offset, item in enumerate(chosen):
    amount = per_folder.get(item.name, 0)
    print(
        f"  {YELLOW}Chapter {first_chapter + offset}{RESET}  {CYAN}{item.name}{RESET}"
        f" {DIM}({amount} page{'' if amount == 1 else 's'}, pages {page:0{w}d}-{page + amount - 1:0{w}d}){RESET}"
    )
    page += amount

def print_shift(plan, info):
  """Say how the pages after the change move."""
  w = plan.width
  tail = [n for n, _ in info.existing if n > plan.end]
  if tail and plan.delta != 0:
    print(
        f"  {BOLD}Shift{RESET}   pages {min(tail):0{w}d}-{max(tail):0{w}d} become "
        f"{min(tail) + plan.delta:0{w}d}-{max(tail) + plan.delta:0{w}d} {DIM}({plan.delta:+d}){RESET}"
    )
  elif not tail:
    print(f"  {DIM}No pages after it, nothing to shift.{RESET}")
  else:
    print(f"  {DIM}Same length, nothing to shift.{RESET}")

def print_totals(plan, info):
  """Total page count and the 3-to-4 digit warning."""
  print(f"\n  {len(info.existing)} pages -> {len(info.existing) + plan.delta} pages in total.")
  if plan.repad:
    print(
        f"\n  {YELLOW}The page count now needs {plan.width} digits, so all "
        f"{len(info.existing)} existing pages are renamed to {plan.width} digits.{RESET}"
    )

def print_folder_name(renamed_folder):
  if renamed_folder is not None:
    print(f"\n  {BOLD}New folder name{RESET}\n\n  {GREEN}{renamed_folder.name}{RESET}")
  else:
    print(f"\n  {YELLOW}The folder will not be renamed (no 'Chapters 1-N' ending, or the new name exists).{RESET}")

def confirm_change():
  """Ask 'Continue?'. Prints the cancel message and returns False on no."""
  if read_confirm("  Continue? (y/n) "):
    return True
  print("\n  Cancelled. Nothing was changed.\n")
  pause()
  return False

def apply_and_finish(folder, plan, info, new_folders, renamed_folder, done_text):
  """Run the change, check the result, then recycle and rename."""
  print()
  try:
    old_dir = splice.apply_splice(
        folder, plan,
        progress=lambda n, t: print(f"\r  Copying pages... {n}/{t}", end="", flush=True),
    )
    print()
  except Exception as exc:
    print(f"\n\n  {RED}Failed: {exc}{RESET}")
    print("  Everything was rolled back. Nothing was changed.\n")
    pause()
    return

  expected = len(info.all_images) - len(plan.removed) + len(plan.placements)
  found = len(list_images(folder))
  if found != expected:
    print(f"\n  {RED}Warning: expected {expected} images but found {found}.{RESET}")
    print("  Nothing was recycled or renamed. Please check the folder.\n")
    pause()
    return

  print()
  to_recycle = ([old_dir] if old_dir else []) + list(new_folders)
  for item in to_recycle:
    error = splice.recycle(item)
    if error is None:
      print(f"  {GREEN}OK{RESET}      {item.name}")
    else:
      print(f"  {RED}FAILED{RESET}  {item.name} ({error})")

  if renamed_folder is not None:
    try:
      folder.rename(renamed_folder)
      print(f"  {GREEN}Renamed{RESET}  {renamed_folder.name}")
    except Exception as exc:
      print(f"  {RED}Could not rename the merged folder ({exc}){RESET}")

  print(f"\n  {GREEN}Done!{RESET} {done_text}\n")
  pause()