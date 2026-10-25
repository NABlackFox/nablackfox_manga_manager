import webbrowser

from utils import BOLD, DIM, RED, RESET, clear_screen, print_header
import functions.read_manga as read_manga

TITLE = "Read mode"


def run_read_mode(manga_root):
  try:
    server, url = read_manga.start_reader(manga_root)
  except Exception as exc:
    clear_screen()
    print_header(manga_root, f"Library: {manga_root}")
    print(f"  {RED}Could not start the reader: {exc}{RESET}\n")
    input(f"  {DIM}Press Enter to go back...{RESET}")
    return

  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print(f"  {BOLD}{TITLE}{RESET}\n")
  print(f"  {url}\n")
  if not webbrowser.open(url):
    print(f"  {DIM}Could not open the browser automatically. Open the address above.{RESET}\n")
  print(f"  {DIM}Middle-click manga to open several side by side. Reader keys: n / p chapter,{RESET}")
  print(f"  {DIM}+ / - width, f fullscreen, h hide the top bar.{RESET}\n")

  try:
    input(f"  {DIM}Press Enter here to stop reading and go back...{RESET}")
  finally:
    server.shutdown()
    server.server_close()