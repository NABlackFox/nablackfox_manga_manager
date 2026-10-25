from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from utils import (
    BOLD, CYAN, DIM, RED, YELLOW, RESET,
    clear_screen, print_header, print_title, parse_selection
)

# Things that ask the user something (keys, text, a folder, a number).

def pause():
  input(f"  {DIM}Press Enter to go back...{RESET}")

def read_text(question):
  """Ask for a line of text; None when cancelled with Esc."""
  kb = KeyBindings()
  @kb.add("escape", eager=True)
  def _cancel(event):
    event.app.exit(result=None)
  return prompt(question, key_bindings=kb)

def read_confirm(question):
  """Ask y/n with one key press; Esc counts as no."""
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

def read_menu_choice(keys, refresh=False):
  """Wait for one of `keys`; returns it, 'esc', or 'refresh' (Ctrl+R) if enabled."""
  kb = KeyBindings()
  @kb.add("<any>")
  def _ignore(event):
    pass
  for key in keys:
    @kb.add(key, eager=True)
    def _pick(event, key=key):
      event.app.exit(result=key)
  @kb.add("escape", eager=True)
  def _back(event):
    event.app.exit(result="esc")
  if refresh:
    @kb.add("c-r", eager=True)
    def _refresh(event):
      event.app.exit(result="refresh")
  return prompt("  > ", key_bindings=kb)

def message_screen(author, lines, manga_root, title):
  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(title, author)
  for line in lines:
    print(f"  {line}")
  print()
  pause()

def print_folder_list(folders, split=None, chosen=()):
  """Numbered folder list. With `split`, folders from that index on are a separate 'merged' group."""
  digits = len(str(len(folders)))
  for number, folder in enumerate(folders, start=1):
    if split is not None and number - 1 == 0 and split > 0:
      print(f"  {BOLD}Unmerged chapters{RESET}\n")
    if split is not None and number - 1 == split:
      if split > 0:
        print()
      print(f"  {BOLD}{RED}Already merged folders (be careful, this combines two merged manga){RESET}\n")
    if folder in chosen:
      print(f"  {DIM}{number:>{digits}}  {folder.name}{RESET}")
    else:
      color = RED if split is not None and number - 1 >= split else CYAN
      print(f"  {YELLOW}{number:>{digits}}{RESET}  {color}{folder.name}{RESET}")

def ask_single_folder(author, folders, title, question, manga_root, split=None):
  error = ""
  while True:
    clear_screen()
    print_header(manga_root, f"Library: {manga_root}")
    print_title(title, author)
    print_folder_list(folders, split)
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

def ask_number(question, show, parse):
  """Ask until `parse` accepts the text; None when cancelled with Esc."""
  error = ""
  while True:
    show(error)
    text = read_text(question)
    if text is None:
      return None
    try:
      return parse(text.strip())
    except ValueError as exc:
      error = str(exc)

def show_merge_screen(author, folders, chosen, error="", title="Merge manga", note="", verb="merged", manga_root=None,
                      noun="folder", chosen_label="Order so far", ordered=True, split=None):
  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print_title(title, author)

  print_folder_list(folders, split, chosen)
  print()

  if chosen:
    print(f"  {BOLD}{chosen_label}{RESET}\n")
    for folder in chosen:
      print(f"  {folder.name}")
    print()

  order_text = f" in the order it should be {verb}" if ordered else ""
  print(f"  {DIM}Enter the number of each {noun}{order_text} (e.g. 3, or 1 4 2, or 5-9).{RESET}")
  print(f"  {DIM}Press Enter on an empty line when you are done.  Esc to cancel.{RESET}\n")
  if note:
    print(f"  {note}\n")
  if error:
    print(f"  {RED}{error}{RESET}\n")

def ask_merge_order(author, folders, manga_root, prompt_label="Folder", **screen):
  """Let the user pick several items in order. None when cancelled.

  Items only need a `.name`. Extra keyword arguments go to show_merge_screen.
  """
  chosen = []
  error = ""
  while True:
    show_merge_screen(author, folders, chosen, error, manga_root=manga_root, **screen)
    error = ""
    text = read_text(f"  {prompt_label} {len(chosen) + 1} > ")
    if text is None:
      return None

    if not text.strip():
      if not chosen:
        error = f"Pick at least one {screen.get('noun', 'folder')} first."
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