from pathlib import Path
import sys
from utils import RED, RESET, clear_screen, enable_ansi, print_header
from pages.author_menu import ask_for_author, run_author_menu

# Mother folder: contains one folder per author, each holding the manga folders
MANGA_ROOT = Path(r"C:\NABlackFoxDisk\Pic\noncheck")

def main():
  enable_ansi()

  if not MANGA_ROOT.is_dir():
    print(f"{RED}Library folder not found: {MANGA_ROOT}{RESET}")
    print("Edit MANGA_ROOT at the top of main.py and try again.")
    sys.exit(1)

  try:
    while True:
      author = ask_for_author(MANGA_ROOT)
      if author is None:
        clear_screen()
        print_header(MANGA_ROOT, f"Library: {MANGA_ROOT}")
        print(f"  {RED}No author folders found in the library.{RESET}\n")
        return
      run_author_menu(author, MANGA_ROOT)
  except (KeyboardInterrupt, EOFError):
    pass

  clear_screen()
  print("Goodbye!")

if __name__ == "__main__":
  main()