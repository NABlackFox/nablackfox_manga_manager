# Manga Manager

A personal tool for keeping a **local manga library** tidy and reading it in your browser.

It has two parts that share one library folder:

- **Terminal side** (the *Manager*): collects downloaded zips, unzips, merges, edits chapters, deletes pages, converts images to WebP.
- **Web side** (the *Reader*): a private reader that runs only on your own computer. Library, search, bookmarks, reading progress, a page/scroll reader.

Nothing is uploaded anywhere. The reader listens on `127.0.0.1` only, so no other device can reach it.

---

## 1. Requirements

- Python 3.10 or newer
- A terminal (Windows Terminal / PowerShell is what it was made for; it also runs on macOS and Linux)
- These Python packages:

```bash
pip install pillow python-dotenv prompt_toolkit send2trash
```

| Package | Used for |
|---|---|
| `pillow` | converting images to WebP, reading image sizes, making thumbnails |
| `python-dotenv` | reading the `.env` settings file |
| `prompt_toolkit` | the interactive menus and author picker in the terminal |
| `send2trash` | sending deleted folders and pages to the recycle bin instead of erasing them |

---

## 2. Setting up the `.env` file

The `.env` file tells the program **where your manga is** and **where your downloaded zips are**.

1. Create a plain text file named exactly `.env` (with the dot, no `.txt`) in the **same folder as `main.py`**.
2. Put these two lines in it, changed to your own folders:

**Windows**

```env
MANGA_ROOT=D:\Manga
ZIP_SOURCE_FOLDER=C:\Users\YourName\Downloads
```

**macOS / Linux**

```env
MANGA_ROOT=/home/yourname/manga
ZIP_SOURCE_FOLDER=/home/yourname/Downloads
```

| Setting | What it is | If you leave it out |
|---|---|---|
| `MANGA_ROOT` | The "mother folder" of your library: one folder per author inside it | a folder called `manga` next to `main.py` |
| `ZIP_SOURCE_FOLDER` | Where your browser saves downloaded zips; used by *Grab zip file* | your user `Downloads` folder |

Tips:

- **Do not put quotes** around the paths. If you do want quotes, use forward slashes (`"D:/Manga"`), because a backslash followed by a letter such as `\n` is read as a special character inside quotes.
- `~` works (for example `~/manga`).
- If the program says *Library folder not found*, the `MANGA_ROOT` path is wrong or the folder does not exist yet. Create it, or fix the path.
- After editing `.env`, restart the program.

---

## 3. Folder structure

`MANGA_ROOT` holds **one folder per author**. Inside each author folder are the **manga folders** (one per manga or per merged manga), and inside those are the page images.

```text
Manga/                                  <- MANGA_ROOT
├── Kuromotokun/                        <- author folder
│   ├── author.webp                     <- optional: an image directly here is the author's picture
│   ├── Some Title.zip <- zip waiting to be unzipped (Unzip manga)
│   ├── Another Title/ <- an unzipped chapter: just pages
│   │   ├── 001.webp
│   │   ├── 002.webp
│   │   └── 003.webp
│   └──Some Title Chapters 1-3/   <- a MERGED manga
│       ├── 001-chapter1.webp           <- first page of chapter 1
│       ├── 002.webp
│       ├── 003.webp
│       ├── 004-chapter2.webp           <- first page of chapter 2
│       ├── 005.webp
│       └── 006-chapter3.webp           <- first page of chapter 3
└── Edogawa Nitro King/
    └── One Shot/
        ├── 001.webp
        └── 002.webp
```

How the names work:

- **Pages** are numbered `001`, `002`, `003`, ... (more digits only for 1000+ pages). The reader shows them in number order.
- **Chapter markers** are part of a page's file name: `004-chapter2.webp` means *chapter 2 starts on page 4*. This is how a merged manga knows where each chapter begins. A folder without markers is read as one long chapter.
- **Merged folder names** end with `Chapters 1-N`. The terminal tools read `N` (the chapter count) from that name.
- **Author picture:** an image sitting directly in an author folder (not inside a manga folder) is used as the author's picture.
- **Hidden folders** (names starting with a dot) are ignored everywhere.

Files the program creates next to `main.py` (safe to delete; they just reset what they remember):

| File | What it remembers |
|---|---|
| `reader_progress.json` | the page you reached in each manga, and when |
| `bookmarks.json` | your bookmarks (which page of which manga) |
| `webp_converted.json` | which folders the WebP converter already finished |
| `.reader_cache/` | small preview thumbnails so the library loads fast |

---

## 4. Starting the program

```bash
python main.py            # asks: 1 = Read, 2 = Manager
python main.py read       # open the reader straight away
python main.py manage     # open the Manager straight away
python main.py -h         # show the help
```

On Windows you can use `py main.py` instead of `python main.py`.

These spellings all work: `read`, `-read`, `--read`, `-r` and `manage`, `manager`, `-manage`, `--manage`, `-manager`, `--manager`, `-m`.

Started **without** an argument, you get the start menu (press `1` or `2`, `Esc` to exit). Started **with** an argument, the program does that one thing and exits when you are done.

---

## 5. Terminal functions

### 5.1 Read mode

Starts the web reader on a free local port, opens your browser at it, and keeps it running. **Press Enter in the terminal to stop it** and go back. (The address changes each time, but your progress and bookmarks are stored in files, so nothing is lost.)

### 5.2 Manager: choosing an author

- Type an author name (Tab completes it) and press Enter to open that author's menu.
- Type `admin` to open the Admin menu.
- Enter on an empty line refreshes the list. `Esc` goes back to the start menu. `Ctrl+C` exits.

### 5.3 Author menu (works on the chosen author's folder)

| # | Function | What it does |
|---|---|---|
| 1 | **Unzip manga** | Finds every `.zip` in the author folder that is not unzipped yet and unzips each into a folder with the zip's name (a single wrapper folder inside the zip is removed). A zip is deleted only after it unzipped successfully; failed zips are kept so you can try again. Asks before doing anything. |
| 2 | **Merge manga** | Pick several chapter folders **in the order you want**. Copies all pages into one new folder, numbered continuously from `001`, and marks the first page of every chapter (`001-chapter1`, `0xx-chapter2`, ...). The folder name is built from the first chapter's name plus `Chapters 1-N`. The source folders go to the recycle bin only after the copy is checked. Warns if the output folder already exists. |
| 3 | **Edit Merged Chapters** | Opens the sub-menu below. |
| 4 | **Edit chapter marker** | Pick a merged folder, a chapter number and the page where that chapter should start. Shows the exact file renames first, asks to confirm, and rolls everything back if a rename fails. This is how a wrong marker is fixed. |
| 5 | **Delete pages** | Pick pages to delete by number (`2`, `1 3 5` or `4-7`). Three separate confirmations. Deleted pages go to the recycle bin, the remaining pages are renumbered from `001`, and chapter markers stay with their chapters. |

**Edit Merged Chapters** sub-menu:

| # | Function | What it does |
|---|---|---|
| 1 | **Add New Chapters** | Puts new chapter folders after the last page of a merged manga. |
| 2 | **Add Missing Chapter** | Inserts a chapter in the middle; the chapters after it shift. |
| 3 | **Update Chapter** | Replaces a chapter with a longer or shorter version; the pages after it shift. |

### 5.4 Admin menu

| # | Function | What it does |
|---|---|---|
| 1 | **Grab zip file** | Scans `ZIP_SOURCE_FOLDER` for downloaded `nhentai*.zip` files, works out the author from the file name (the `[Group (Artist)]` part), and matches it to your author folders. Shows the full plan (matched / not matched) and moves the zips only after you confirm. For unmatched authors it offers to create a new author folder (zips are **not** moved then; run it again afterwards). |
| 2 | **Grab zip file (manual mode)** | You pick the zips by hand, pick the author by name, confirm, and they are moved. Repeats until you are done. |
| 3 | **Convert images to WebP and fix page names** | Goes through every chapter folder and does two things in order: (1) **type**: images that are not `.webp` are converted (an existing `.webp` is left alone, animated images are skipped); (2) **naming**: if the pages are not already `001.webp`, `002.webp`, ... (same digit count, at least 3) the whole folder is renamed that way in reading order, keeping any `-chapterN` marker on its page. Pages are renamed in two steps and everything is undone if one fails. Images directly in an author folder are converted but never renamed. Finished folders are remembered in `webp_converted.json`; delete that file to make it check everything again. |

---

## 6. Web functions

### 6.1 Library (home page)

- Authors listed in sections with a **letter bar** (A–Z, `#`) to jump around. Each author shows one row with **Show more / Show less**.
- **Continue reading** row: the manga you are in the middle of, newest first. Clicking one resumes at the exact place you stopped. It hides while you search or filter, and finished manga are left out.
- **Search** (press `/`): filters manga **and** authors across the whole library. `Enter` with exactly one match opens it. `Esc` clears.
- **Filter buttons**: All, Unread, In progress, Finished. Your choice is remembered.
- **Random** button (or press `r`): opens a random manga from what is currently shown (pick *Unread* first to get a random unread one).
- Each card shows a progress bar, a **Finished** badge when you reached the last page, and a star to **bookmark**. A bookmarked card shows where, for example `★ Chapter 3 · page 45`.
- `/?q=something` opens the library already filtered.

### 6.2 Author page

Same cards, filters, search and random button, limited to one author.

### 6.3 Manga page

- Cover, author, facts (pages, chapters) and your **progress meter**.
- **Start reading** / **Continue from page N**, and **From the start**.
- **Bookmark** star: bookmarking from here marks the **first chapter**. The button shows what is marked.
- **Go to bookmark**: opens the reader on the bookmarked page.
- **Mark as finished**: moves your saved place to the last page (asks first if you have progress).
- **Mark as unread**: forgets your saved page (bookmarks are kept).
- **Page preview**: thumbnails of the pages, **Load 10 more** or **Load all** (images load as you scroll).
- **Search all manga** box (press `/`) that jumps to the library with the results.

### 6.4 Reader

- **Page mode** (one page at a time; click the left half to go back, the right half to go forward) and **Scroll mode** (a long vertical strip). Switch with `m`.
- **Chapter dropdown** and previous / next chapter buttons.
- **Fit screen / Fit width** (`w`) and **wider / narrower** (`+` / `-`).
- Fullscreen (`f`), and a top bar that hides itself (`h` locks it hidden). A thin progress line shows how far you are.
- Your position is **saved automatically** as you read.
- **Bookmark this page** (`b`): marks the page you are on. Click again on that page to remove it; click on another page to **move** the bookmark there. The star is filled on the bookmarked page and outlined when the bookmark is elsewhere.
- **+ Chapter** (`c`): starts a new chapter on the page you are reading (details below).

**+ Chapter rules** (for merged folders whose pages are numbered like `001.webp`):

- No chapter markers yet: the first page becomes Chapter 1 and the current page Chapter 2 (just Chapter 1 if you are on the first page).
- Markers already exist: the current page becomes *last chapter number + 1*, and only if it comes **after** the last chapter's start.
- A popup shows exactly which pages will be renamed and asks you to confirm. Only page file names change, never the folder name.
- It refuses (with a message) if the page already starts a chapter, comes before the last marker, is not numbered like `001.png`, or its number exists twice. A wrong marker can only be fixed from the terminal (*Edit chapter marker*).
- Note: if the folder name says `Chapters 1-X` and you add chapters beyond `X`, the terminal tools still read `X` from the name until you rename the folder.

### 6.5 Bookmarks page

- Everything you bookmarked, with the marked chapter and page on each card.
- Clicking a card opens the reader **on the bookmarked page**.
- Filter box (press `/`). The star on a card removes the bookmark (and brings it back as the first chapter if clicked again).
- A small counter next to **Bookmarks** in the top bar shows how many you have.

### 6.6 Everywhere

- Press `?` on any page to see the keyboard shortcuts for that page.
- Footer link **Clear all reading progress**: forgets the progress of every manga (asks first; bookmarks are kept).

### 6.7 Keyboard shortcuts

| Where | Key | Action |
|---|---|---|
| Library | `/` | search |
| Library | `Enter` | open the match (when one is left) |
| Library | `Esc` | clear the search |
| Library | `r` | random manga |
| Manga page | `/` | search all manga |
| Bookmarks | `/` | filter bookmarks |
| Reader (page mode) | `←` `→`, `PageUp` `PageDown`, `Space` | previous / next page (Shift+Space goes back) |
| Reader (page mode) | `Home` `End` | first / last page |
| Reader | `p` `n` (or `[` `]`) | previous / next chapter |
| Reader | `b` | bookmark this page |
| Reader | `c` | start a new chapter on this page |
| Reader | `m` | page mode / scroll mode |
| Reader | `w` | fit screen / fit width |
| Reader | `+` `-` | wider / narrower |
| Reader | `f` | fullscreen |
| Reader | `h` | lock the top bar hidden |
| Any page | `?` | show / hide the shortcut list |

---

## 7. Good to know

- **Bookmarks and progress are different things.** Progress is where you stopped reading (automatic). A bookmark is a page you marked on purpose. Resetting progress never removes bookmarks.
- **Nothing expires.** Progress and bookmarks stay in their files until you change them; there is no timeout. Use *Mark as unread*, or *Clear all reading progress* in the footer, to reset.
- **Deleted means recycle bin.** Merging and page deletion use the recycle bin, so mistakes can be undone from there. Unzipping deletes the zip only after a successful unzip.
- **Back up the library** before the first run of *Convert images to WebP and fix page names* on a large library; it renames many files.
- **Page names matter.** Pages are shown in the order of the numbers in their file names, so keep names like `001`, `002`, ... (the WebP converter does this for you).
