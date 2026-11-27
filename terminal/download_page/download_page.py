import webbrowser

import config
from terminal.shared.utils import BOLD, DIM, RED, RESET, YELLOW, clear_screen, print_header
from admin.server import start_server

TITLE = "Download mode"


def run_download_mode(manga_root):
  try:
    server, url = start_server()
  except Exception as exc:
    clear_screen()
    print_header(manga_root, f"Library: {manga_root}")
    print(f"  {RED}Could not start the downloader: {exc}{RESET}\n")
    input(f"  {DIM}Press Enter to go back...{RESET}")
    return

  clear_screen()
  print_header(manga_root, f"Library: {manga_root}")
  print(f"  {BOLD}{TITLE}{RESET}\n")
  print(f"  {url}\n")
  if not config.NHENTAI_API_KEY:
    print(f"  {YELLOW}No API key found.{RESET} Add NHENTAI_API_KEY=... to the .env file and restart.\n")
  if not webbrowser.open(url):
    print(f"  {DIM}Could not open the browser automatically. Open the address above.{RESET}\n")
  print(f"  {DIM}Search an author, pick manga, press Download. Zips are saved to:{RESET}")
  print(f"  {config.ZIP_SOURCE_FOLDER}")
  print(f"  {DIM}Then use Admin > Grab zip file here in the terminal.{RESET}\n")

  try:
    input(f"  {DIM}Press Enter here to stop (waiting downloads are dropped) and go back...{RESET}")
  finally:
    server.queue.shutdown()
    server.shutdown()
    server.server_close()
