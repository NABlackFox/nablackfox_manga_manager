/* common.js — small helpers shared by every page (exposed as window.MM) */
window.MM = (() => {
  const $ = (id) => document.getElementById(id);
  const enc = encodeURIComponent;
  const params = new URLSearchParams(location.search);

  // localStorage can be blocked or full: never let that break the page
  const store = {
    get(key) { try { return localStorage.getItem(key); } catch (_) { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch (_) {} },
  };

  // "a=<author>&m=<manga>" for API / image URLs
  const mangaQuery = (author, manga) => "a=" + enc(author || "") + "&m=" + enc(manga || "");

  // The first letter of a name, A-Z, or "#" for numbers and symbols (same rule as group_key in terminal/utils.py)
  function groupKey(name) {
    const first = name.normalize("NFD")[0] || "";
    return /\p{L}/u.test(first) ? first.toUpperCase() : "#";
  }

  async function getJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw Object.assign(new Error(res.statusText), { status: res.status });
    return res.json();
  }

  // ---------- bookmarks ----------
  const STAR = '<svg class="bm-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.5l2.6 5.5 6 .8-4.4 4.2 1.1 6-5.3-2.9-5.3 2.9 1.1-6L3.4 9.8l6-.8z" stroke-linejoin="round"/></svg>';

  async function refreshBookmarkCount() {
    const badge = $("bm-count");
    if (!badge) return;
    try {
      const n = (await getJson("/api/bookmarks")).length;
      badge.textContent = n;
      badge.hidden = n === 0;
    } catch (_) {}
  }

  // "Chapter 3 · page 45" for a bookmark {page, chapter}
  function markText(mark) {
    if (!mark) return "";
    const parts = [];
    if (mark.chapter) parts.push("Chapter " + mark.chapter);
    if (mark.page) parts.push("page " + mark.page);
    return parts.join(" · ") || "Bookmarked";
  }

  // Make a button control the bookmark of one manga. `mark` is the current bookmark {page, chapter} or null.
  // Without getIndex (library, manga page) a click adds the bookmark (the server picks the first chapter) or removes it.
  // With getIndex (reader) it marks the page you are on: click again there to remove it, click on another page to move it.
  // Updates at once, undoes itself if the save fails. onChange gets the new bookmark (or null).
  function bindBookmark(btn, author, manga, mark, onChange, getIndex) {
    if (mark === true) mark = { page: 0, chapter: null };   // stale cached data from before page bookmarks
    mark = mark || null;
    let busy = false;
    const isHere = () => !!mark && (!getIndex || mark.page === getIndex() + 1);
    const paint = () => {
      const here = isHere();
      btn.classList.toggle("on", here);
      btn.classList.toggle("elsewhere", !!mark && !here);
      btn.setAttribute("aria-pressed", here);
      const text = markText(mark);
      btn.title = !mark ? (getIndex ? "Bookmark this page (b)" : "Bookmark (read later)")
        : here ? "Bookmarked: " + text + " (click to remove)"
        : "Bookmarked: " + text + " (click to move it to this page)";
      const label = btn.querySelector(".label");
      if (label) label.textContent = mark ? "Bookmarked · " + text : "Bookmark";
    };
    paint();
    btn.addEventListener("click", async (e) => {
      e.preventDefault(); e.stopPropagation();   // a card is a link: don't open it
      if (busy) return;
      busy = true;
      const before = mark;
      const remove = isHere();
      const index = getIndex ? getIndex() : undefined;
      mark = remove ? null : { page: index === undefined ? 0 : index + 1, chapter: null }; paint();
      try {
        const res = await fetch("/api/bookmark?" + mangaQuery(author, manga), {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(remove ? { on: false } : { on: true, index }),
        });
        if (!res.ok) throw new Error();
        mark = remove ? null : await res.json();   // the server says which page / chapter it really marked
        paint();
        if (onChange) onChange(mark);
        refreshBookmarkCount();
      } catch (_) { mark = before; paint(); }
      busy = false;
    });
    return { set(value) { mark = value || null; paint(); }, refresh: paint, toggle() { btn.click(); } };
  }

  // ---------- manga card (library + bookmarks page) ----------
  // name: the folder name. meta: the short meta.json information from the server (or null); when there is one its
  //   title is shown instead of the folder name, and the card remembers what to search in (box.doc).
  // pages: the page count, searchable as pages:>30.
  // href: where the card opens (default: the manga page).
  // readAtMark: open the reader at the bookmarked page instead (falls back to the manga page without a bookmark).
  function card({ author, manga, name, sub, progress, bookmarked, onBookmark, href, readAtMark, meta, pages }) {
    const q = mangaQuery(author, manga);
    const shown = MM.meta.title(meta, name);
    const box = document.createElement("div");
    box.className = "card";
    box.doc = MM.meta.doc({ name, author, pages, meta });
    box.dataset.status = progress >= 1 ? "done" : progress > 0 ? "reading" : "unread";

    const a = document.createElement("a");
    a.className = "card-link"; a.href = href || "/manga?" + q;

    const cover = document.createElement("div");
    cover.className = "cover";
    const initial = document.createElement("div");
    initial.className = "initial";
    initial.textContent = (shown.trim()[0] || "?").toUpperCase();
    cover.appendChild(initial);
    const img = document.createElement("img");
    img.loading = "lazy"; img.alt = ""; img.src = "/thumb?" + q;
    img.onload = () => initial.remove();
    img.onerror = () => img.remove();
    cover.appendChild(img);
    if (progress >= 1) {
      const done = document.createElement("span");
      done.className = "badge done"; done.textContent = "Finished";
      cover.appendChild(done);
    }
    if (progress > 0) {
      const bar = document.createElement("div");
      bar.className = "progress"; bar.style.width = Math.min(progress, 1) * 100 + "%";
      cover.appendChild(bar);
    }
    a.appendChild(cover);

    const title = document.createElement("div");
    title.className = "name"; title.textContent = shown;
    title.title = meta && meta.japanese && meta.japanese !== shown ? shown + "\n" + meta.japanese : shown;
    a.appendChild(title);
    if (sub) {
      const s = document.createElement("div");
      s.className = "sub"; s.textContent = sub;
      a.appendChild(s);
    }
    const note = document.createElement("div");
    note.className = "mark-note";
    a.appendChild(note);
    box.appendChild(a);

    // the star sits on top of the cover, next to the link (not inside it)
    const star = document.createElement("button");
    star.type = "button"; star.className = "bm"; star.innerHTML = STAR;
    box.appendChild(star);
    const showMark = (mark) => {
      note.textContent = mark ? "★ " + markText(mark) : ""; note.hidden = !mark;
      if (readAtMark && !href) a.href = mark && mark.page ? "/read?" + q + "&p=" + mark.page : "/manga?" + q;
    };
    const initial_mark = bookmarked === true ? { page: 0, chapter: null } : bookmarked || null;
    showMark(initial_mark);
    bindBookmark(star, author, manga, initial_mark, (mark) => {
      showMark(mark);
      box.classList.toggle("unmarked", !mark);
      if (onBookmark) onBookmark(mark);
    });
    return box;
  }

  // ---------- keyboard shortcut list (press ?) ----------
  // list: [["key", "what it does"], ...]  The page shows it as a small overlay.
  function shortcuts(list) {
    let overlay = null;
    const close = () => { if (overlay) { overlay.remove(); overlay = null; } };
    const open = () => {
      overlay = document.createElement("div");
      overlay.className = "help-overlay";
      const box = document.createElement("div");
      box.className = "help-box";
      const title = document.createElement("h2");
      title.textContent = "Keyboard shortcuts";
      const dl = document.createElement("dl");
      for (const [keys, text] of list.concat([["?", "Show / hide this list"]])) {
        if (keys === "#") {              // a heading row
          const h = document.createElement("h3");
          h.className = "help-sub"; h.textContent = text;
          dl.appendChild(h);
          continue;
        }
        const dt = document.createElement("dt");
        keys.split(" ").forEach((k) => { const kbd = document.createElement("kbd"); kbd.textContent = k; dt.appendChild(kbd); });
        const dd = document.createElement("dd");
        dd.textContent = text;
        dl.append(dt, dd);
      }
      box.append(title, dl);
      overlay.appendChild(box);
      overlay.addEventListener("click", close);
      document.body.appendChild(overlay);
    };
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) return;
      if (e.key === "?") { overlay ? close() : open(); e.preventDefault(); }
      else if (e.key === "Escape" && overlay) close();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    refreshBookmarkCount();
    // footer: forget the reading position of every manga (bookmarks are kept)
    const clearAll = $("clear-all");
    if (clearAll) clearAll.addEventListener("click", async () => {
      if (!confirm("Clear the reading progress of ALL manga? Bookmarks are kept. This cannot be undone.")) return;
      try {
        const res = await fetch("/api/progress/clear-all", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        if (!res.ok) throw new Error();
        try { localStorage.removeItem("library-cache-v3"); } catch (_) {}   // the cached library still has the old progress
        location.reload();
      } catch (_) { alert("Could not clear. Is read mode still running in the terminal?"); }
    });
    // pages with a "search all manga" box that jumps to the library: "/" focuses it
    const quick = $("quick-search");
    if (quick) document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement !== quick && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); quick.focus(); }
      else if (e.key === "Escape" && document.activeElement === quick) quick.blur();
    });
  });

  return { $, enc, params, store, mangaQuery, groupKey, getJson, card, bindBookmark, refreshBookmarkCount, shortcuts };
})();