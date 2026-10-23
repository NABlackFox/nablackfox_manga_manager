from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from utils import (
    BOLD, CYAN, DIM, GREEN, RED, YELLOW, RESET,
    clear_screen, print_header, print_title, parse_selection, list_subfolders,
    is_inside
)
import functions.merge_manga as merge_manga

def read_text(question):
  kb = KeyBindings()
  @kb.add("escape", eager=True)
  def _cancel(event):
    event.app.exit(result=None)
  return prompt(question, key_bindings=kb)

def read_confirm(question):
  kb = KeyBindings()
  @kb.add("<any>")
  def _ignore(event):
    pass
  for key in ("y", "Y"):
    @kb.add(key, eager=True)
    def _yes(event):
      event.app.exit(result=True)
  for key in ("n", "N", "escape"):
    @kb.add(key, eager=True)
    def _no(event):
      event.app.exit(result=False)
  return prompt(question, key_bindings=kb)

def show_merge_screen(author, folders, chosen, error="", title="Merge manga", note="", verb="merged", manga_root=None):
  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(title, author)

  digits = len(str(len(folders)))
  for number, folder in enumerate(folders, start=1):
    if folder in chosen:
      print(f"  {DIM}{number:>{digits}}  {folder.name}{RESET}")
    else:
      print(f"  {YELLOW}{number:>{digits}}{RESET}  {CYAN}{folder.name}{RESET}")
  print()

  if chosen:
    print(f"  {BOLD}Order so far{RESET}\n")
    for folder in chosen:
      print(f"  {folder.name}")
    print()

  print(f"  {DIM}Enter the number of each folder in the order it should be {verb} (e.g. 3, or 1 4 2, or 5-9).{RESET}")
  print(f"  {DIM}Press Enter on an empty line when you are done.  Esc to cancel.{RESET}\n")
  if note:
    print(f"  {note}\n")
  if error:
    print(f"  {RED}{error}{RESET}\n")

def ask_merge_order(author, folders, manga_root, **screen):
  chosen = []
  error = ""
  while True:
    show_merge_screen(author, folders, chosen, error, manga_root=manga_root, **screen)
    error = ""
    text = read_text(f"  Folder {len(chosen) + 1} > ")
    if text is None:
      return None

    if not text.strip():
      if not chosen:
        error = "Pick at least one folder first."
        continue
      return chosen

    try:
      numbers = parse_selection(text, len(folders))
    except ValueError as exc:
      error = str(exc)
      continue

    already = []
    for number in numbers:
      folder = folders[number - 1]
      if folder in chosen:
        already.append(str(number))
      else:
        chosen.append(folder)
    if already:
      error = f"Already added, skipped: {', '.join(already)}"

def merge_message_screen(author, lines, manga_root, title="Merge manga"):
  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(title, author)
  for line in lines:
    print(f"  {line}")
  print()
  input(f"  {DIM}Press Enter to go back...{RESET}")

def run_merge(author, manga_root):
  author_folder = manga_root / author
  folders = list_subfolders(author_folder)
  if not folders:
    merge_message_screen(author, ["No folders to merge in this author folder."], manga_root)
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
    merge_message_screen(author, [f"{RED}No image files found in the selected folders.{RESET}"], manga_root)
    return
  if any(is_inside(output_folder, f) for f in chosen):
    merge_message_screen(
        author,
        [f"{RED}The output folder name matches one of the selected folders:{RESET}", merged_name],
        manga_root
    )
    return

  pages = {}
  for _file, label in plan:
    pages[label] = pages.get(label, 0) + 1

  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title("Merge manga", author)
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
    input(f"  {DIM}Press Enter to go back...{RESET}")
    return

  print()
  try:
    for number, total in merge_manga.copy_pages(plan, output_folder):
      print(f"\r  Copying pages... {number}/{total}", end="", flush=True)
    print()
  except Exception as error:
    print(f"\n\n  {RED}Copy failed: {error}{RESET}")
    print("  The source folders were NOT touched.\n")
    input(f"  {DIM}Press Enter to go back...{RESET}")
    return

  copied = len(merge_manga.list_images(output_folder))
  if copied < len(plan):
    print(f"\n  {RED}Warning: expected at least {len(plan)} images in the output folder but found {copied}.{RESET}")
    print("  The source folders were NOT touched.\n")
    input(f"  {DIM}Press Enter to go back...{RESET}")
    return

  print()
  for folder, error in merge_manga.recycle_folders(chosen):
    if error is None:
      print(f"  {GREEN}OK{RESET}      {folder.name}")
    else:
      print(f"  {RED}FAILED{RESET}  {folder.name} ({error})")
  print(f"\n  {GREEN}Done!{RESET} {len(plan)} pages merged. The source folders are in the recycle bin\n  if you need them back.")
  print()
  input(f"  {DIM}Press Enter to go back...{RESET}")