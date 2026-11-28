# Manga Manager

A personal tool for keeping a **local manga library** tidy and reading it in your browser.

It has two parts that share one library folder:

- **Terminal side** (the *Manager*): collects downloaded zips, unzips, merges, edits chapters, deletes pages, converts images to WebP.
- **Web side** (the *Reader*): a private reader that runs only on your own computer. Library, search, bookmarks, reading progress, a page/scroll reader.
- **Downloader** (optional): a second local web page that searches an author through the nhentai API and downloads the zips you pick into your zip folder.

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
| `ZIP_SOURCE_FOLDER` | Where your browser saves downloaded zips; used by *Grab zip file* and by the downloader | your user `Downloads` folder |
| `NHENTAI_API_KEY` | Your API key from the nhentai account settings (downloader only) | the downloader works but asks for a key |
| `NHENTAI_HIDE_TAGS` | Tags the downloader should never show: tag names and/or tag ids, separated by commas | nothing hidden |

Optional extras for the downloader: `NHENTAI_USER_AGENT` (how the tool introduces itself to the API), `NHENTAI_API_BASE` (defaults to `https://nhentai.net/api/v2`), and the per-minute limits `NHENTAI_SEARCH_PER_MINUTE` (12), `NHENTAI_DETAIL_PER_MINUTE` (30), `NHENTAI_DOWNLOAD_PER_MINUTE` (6).

Example `.env` with the downloader set up:

```env
MANGA_ROOT=D:\Manga
ZIP_SOURCE_FOLDER=C:\Users\YourName\Downloads
NHENTAI_API_KEY=paste-your-key-here
NHENTAI_HIDE_TAGS=some tag, 12345
```

Keep the key private: never paste it into chat, a screenshot or a shared folder. It is only used by the local downloader server, never by the reading pages.

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
│   ├── nhentai-325605 - Some Title.zip <- zip waiting to be unzipped (Unzip manga)
│   ├── nhentai-430708 - Another Title/ <- an unzipped chapter: pages + meta.json
│   │   ├── meta.json                   <- optional: title, tags, likes ... (see 6.8)
│   │   ├── 001.webp
│   │   ├── 002.webp
│   │   └── 003.webp
│   └── [Kuromotokun] 325605 Some Title Chapters 1-3/   <- a MERGED manga
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
- **`meta.json`** (optional) sits next to the pages and holds the gallery information the downloader saved: title, Japanese title, tags, likes, upload date. The reader shows it and searches it (6.8). A manga without one works exactly as before.
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
python main.py            # asks: 1 = Read, 2 = Manager, 3 = Download
python main.py read       # open the reader straight away
python main.py manage     # open the Manager straight away
python main.py download   # open the Downloader straight away
python main.py -h         # show the help
```

On Windows you can use `py main.py` instead of `python main.py`.

These spellings all work: `read`, `-read`, `--read`, `-r`; `manage`, `manager`, `-manage`, `--manage`, `-manager`, `--manager`, `-m`; `download`, `-download`, `--download`, `-d`.

Started **without** an argument, you get the start menu (press `1`, `2` or `3`, `Esc` to exit). Started **with** an argument, the program does that one thing and exits when you are done.

---

## 5. Terminal functions

### 5.1 Read mode

Starts the web reader on a free local port, opens your browser at it, and keeps it running. **Press Enter in the terminal to stop it** and go back. (The address changes each time, but your progress and bookmarks are stored in files, so nothing is lost.)

### 5.2 Download mode

Starts the downloader (section 7) on its own free local port and opens it in your browser. It warns you if no `NHENTAI_API_KEY` is set. **Press Enter in the terminal to stop it** and go back; downloads still waiting are dropped. The zips it saves are then handled by **Admin > Grab zip file** in the Manager, as before.

### 5.3 Manager: choosing an author

- Type an author name (Tab completes it) and press Enter to open that author's menu.
- Type `admin` to open the Admin menu.
- Enter on an empty line refreshes the list. `Esc` goes back to the start menu. `Ctrl+C` exits.

### 5.4 Author menu (works on the chosen author's folder)

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

### 5.5 Admin menu

| # | Function | What it does |
|---|---|---|
| 1 | **Grab zip file** | Scans `ZIP_SOURCE_FOLDER` for downloaded `nhentai*.zip` files, works out the author from the file name (the `[Group (Artist)]` part), and matches it to your author folders. Shows the full plan (matched / not matched) and moves the zips only after you confirm. For unmatched authors it offers to create a new author folder (zips are **not** moved then; run it again afterwards). |
| 2 | **Grab zip file (manual mode)** | You pick the zips by hand, pick the author by name, confirm, and they are moved. Repeats until you are done. |
| 3 | **Convert images to WebP and fix page names** | Goes through every chapter folder and does two things in order: (1) **type**: images that are not `.webp` are converted (an existing `.webp` is left alone, animated images are skipped); (2) **naming**: if the pages are not already `001.webp`, `002.webp`, ... (same digit count, at least 3) the whole folder is renamed that way in reading order, keeping any `-chapterN` marker on its page. Pages are renamed in two steps and everything is undone if one fails. Images directly in an author folder are converted but never renamed. Finished folders are remembered in `webp_converted.json`; delete that file to make it check everything again. |

---

## 6. Web functions (the reader)

### 6.1 Library (home page)

- Authors listed in sections with a **letter bar** (A–Z, `#`) to jump around. Each author shows one row with **Show more / Show less**.
- **Continue reading** row: the manga you are in the middle of, newest first. Clicking one resumes at the exact place you stopped. It hides while you search or filter, and finished manga are left out.
- **Search** (press `/`): filters across the whole library by title, author, tags and more (see 6.8 for tags, `-tag:`, `pages:>30` ...). `Enter` with exactly one match opens it. `Esc` clears.
- **Tags** button (or press `t`): a panel with every tag in the library and how many manga have it. Click a tag to show only manga that have it, click again to hide the ones that do, once more to clear it. It just edits the search box, so you can also type or edit the filter by hand.
- **Filter buttons**: All, Unread, In progress, Finished. Your choice is remembered.
- **Random** button (or press `r`): opens a random manga from what is currently shown (pick *Unread* first to get a random unread one).
- Each card shows the title from `meta.json` (the folder name when there is none), the page count, the likes (`♥ 13.5K`), a progress bar, a **Finished** badge when you reached the last page, and a star to **bookmark**. A bookmarked card shows where, for example `★ Chapter 3 · page 45`.
- `/?q=something` opens the library already filtered.

### 6.2 Author page

Same cards, filters, search and random button, limited to one author.

### 6.3 Manga page

- Cover, author, the title and Japanese title, facts (pages, chapters, ID, likes, upload date, scanlator) and your **progress meter**.
- **Tags**, grouped as Groups, Parodies, Categories, Languages and Tags. Click any tag to see every manga with it. (Only for manga that have a `meta.json`.)
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
- **Info** button (`i`): title, facts and tags of the manga you are reading (only when it has a `meta.json`). A tag opens the filtered library in a new tab, so the reader keeps your place.
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
- Filter box (press `/`), with the same search language as the library (6.8). The star on a card removes the bookmark (and brings it back as the first chapter if clicked again).
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
| Library | `t` | show / hide the tag filter |
| Manga page | `/` | search all manga |
| Bookmarks | `/` | filter bookmarks |
| Reader (page mode) | `←` `→`, `PageUp` `PageDown`, `Space` | previous / next page (Shift+Space goes back) |
| Reader (page mode) | `Home` `End` | first / last page |
| Reader | `p` `n` (or `[` `]`) | previous / next chapter |
| Reader | `b` | bookmark this page |
| Reader | `i` | info: title, facts, tags |
| Reader | `c` | start a new chapter on this page |
| Reader | `m` | page mode / scroll mode |
| Reader | `w` | fit screen / fit width |
| Reader | `+` `-` | wider / narrower |
| Reader | `f` | fullscreen |
| Reader | `h` | lock the top bar hidden |
| Any page | `?` | show / hide the shortcut list |

### 6.8 Search language and `meta.json`

The search box on the library, author and bookmarks pages understands these. Several words can be combined; **all** of them must match.

| Type | It finds |
|---|---|
| `glasses` | a word in the folder name, either title, author, scanlator, ID or any tag |
| `"big breasts"` | a phrase (quotes) |
| `tag:glasses` | has a tag containing "glasses" (any kind of tag). With quotes, `tag:"glasses"`, only that exact tag |
| `artist:` `group:` `parody:` `character:` `language:` `category:` | the same, limited to that kind of tag |
| `-tag:ahegao`, `-glasses` | **without** it: a minus works in front of anything |
| `title:` `author:` `scanlator:` | search only that field (`author:` is the library folder) |
| `pages:>30`, `pages:20-40`, `pages:<=12` | number of pages |
| `favorites:>1k` (also `likes:`) | likes. `k` = thousand, `m` = million |
| `year:2021`, `year:2019-2021` | year it was uploaded |
| `id:374818` | the gallery ID |
| `has:meta`, `-has:meta` | only manga with / without a `meta.json` (handy for finding old ones) |

Example: `tag:glasses -tag:ahegao language:english pages:>20 favorites:>1k`.

Notes: capitals do not matter. A half-typed term such as `tag:` or `pages:>` is ignored until it is complete. A word with a prefix that is not in the list (such as `re:zero`) is searched as an ordinary word. Press `?` on these pages for this list.

What the reader reads from `meta.json`: `id`, `title.english` / `title.japanese` / `title.pretty`, `upload_date`, `num_favorites`, `scanlator` and `tags` (each with a `type` and a `name`). Pages come from the real image count, not `num_pages`. The file comes from the internet, so every value is checked and shortened, shown only as plain text, and a missing or broken file simply means "no information". Files over 2 MB are ignored.

Merged manga (*Merge manga*) are new folders made of pages only, so they carry no `meta.json` and show their folder name.

---

## 7. Downloader (admin web page)

A separate local page, started with `python main.py download`. It runs on its own port, so your API key never goes near the reading pages. It is a modular monolith in the `admin/` folder: `shared` (API client, rate limiting), `search` (author search and the tag filter) and `downloads` (the queue); each module has its own templates and static files.

How you use it:

1. Find an author you like on the main site, then type the author's name in the search box and press Enter. Choose **Artist** (exact artist tag) or **Any text** (also finds circle / group names inside titles).
2. You get the author's manga, newest first, with covers, page count and likes. A badge shows **In library** (you already have it) or **Zip waiting** (the zip is already in the zip folder). **Load more** shows the next page of results.
3. Click manga to tick them (or **Select all new**, which skips the ones you already have), then press **Download**.
4. The **Downloads** panel shows each one: waiting, downloading with a progress bar, saved, skipped or failed (with the reason and *Try again*). **Cancel waiting** and **Clear finished** tidy the list.
5. The zips land in `ZIP_SOURCE_FOLDER`, named `nhentai-<id> - <title>.zip`. Then use the terminal as usual: **Admin > Grab zip file**, **Unzip manga**, **Convert to WebP**, **Merge manga**.

**The filter (hide tags).** Open *Filters* and list the tags you do not want to see, separated by commas. A **name** is added to the search as `-tag:"name"`; a **number** is a tag id and hides any result that carries it. Results with tags blacklisted on your account are hidden too (tick box). You can also put the list in `.env` as `NHENTAI_HIDE_TAGS`. The exact tag names or ids are for you to fill in.

**Rate limits.** Every call waits for its slot so the API's per-minute limits are respected (search 12/min, details 30/min, downloads 6/min by default, below the documented limits). If the site answers "too many requests" the downloader waits as long as it asks and tries again, up to 4 times. Downloads run one at a time.

**Safety.**
- Both local servers (reader and downloader) listen on `127.0.0.1` only and refuse requests that do not come from their own pages, so another website open in your browser cannot make them do anything.
- The API key is sent to the API only (never to the image or zip servers) and is never shown in a page.
- Every downloaded zip is checked **before it is kept**, without extracting it: it must be a real zip, must not hold programs or scripts (`.exe`, `.bat`, `.js`, `.html`, `.svg`, ...), must not use file paths that point outside its folder, and must not unzip to an absurd size. A zip that fails is deleted and the job says why. Unzipping in the Manager also blocks unsafe paths, and the reader only ever opens image files.
- What cannot be removed: downloading means the site sees your IP address and which account's key you use, and image libraries (Pillow) occasionally have security bugs, so keep it updated with `pip install -U pillow`.

Good to know: the API's exact answers could not be tested without a key, so if something looks off (no covers, an unexpected answer, downloads refused) the page shows the reason. Downloading needs a key that is allowed to download.

---

## 8. Good to know

- **Bookmarks and progress are different things.** Progress is where you stopped reading (automatic). A bookmark is a page you marked on purpose. Resetting progress never removes bookmarks.
- **Nothing expires.** Progress and bookmarks stay in their files until you change them; there is no timeout. Use *Mark as unread*, or *Clear all reading progress* in the footer, to reset.
- **Deleted means recycle bin.** Merging and page deletion use the recycle bin, so mistakes can be undone from there. Unzipping deletes the zip only after a successful unzip.
- **Back up the library** before the first run of *Convert images to WebP and fix page names* on a large library; it renames many files.
- **Page names matter.** Pages are shown in the order of the numbers in their file names, so keep names like `001`, `002`, ... (the WebP converter does this for you).
