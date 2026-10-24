from utils import BOLD, DIM, GREEN, RED, RESET, clear_screen, print_header
from helpers.prompts import read_confirm, pause
import functions.unzip_manga as unzip_manga

def ask_continue(zips):
  print(f"  {BOLD}Ready to unzip{RESET}\n")
  for zip_file in zips:
    print(f"  {RED}{zip_file.name}{RESET}")
  print(f"\n  {DIM}Each zip is deleted after it is unzipped successfully.{RESET}\n")
  return read_confirm("  Continue? (y/n) ")

def run_unzip(author, manga_root):
  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print(f"  {BOLD}Unzip manga{RESET} {DIM}-{RESET} {GREEN}{author}{RESET}\n")
  folder = manga_root / author
  to_unzip, skipped = unzip_manga.find_new_zips(folder)

  print(
      f"  Found {BOLD}{len(to_unzip) + skipped}{RESET} zip(s):"
      f" {GREEN}{len(to_unzip)} new{RESET},"
      f" {DIM}{skipped} already unzipped{RESET}.\n"
  )

  if not to_unzip:
    print("  Nothing to unzip.")
  elif not ask_continue(to_unzip):
    print("\n  Cancelled. Nothing was changed.")
  else:
    print()
    failed = []
    for number, zip_file, error in unzip_manga.unzip_zips(folder, to_unzip):
      progress = f"[{number}/{len(to_unzip)}]"
      if error is None:
        print(f"  {progress} {GREEN}OK{RESET}      {zip_file.name}")
      else:
        print(f"  {progress} {RED}FAILED{RESET}  {zip_file.name} ({error})")
        failed.append(zip_file.name)

    if failed:
      print(f"\n  {RED}Finished with {len(failed)} failure(s):{RESET}")
      for name in failed:
        print(f"    - {name}")
      print(f"  {DIM}The failed zips were kept, so you can try again.{RESET}")
    else:
      print(f"\n  {GREEN}Done!{RESET} {len(to_unzip)} zip(s) unzipped and deleted.")

  print()
  pause()