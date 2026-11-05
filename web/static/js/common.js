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

  // Make a button toggle the bookmark of one manga. Updates at once, undoes itself if the save fails.
  function bindBookmark(btn, author, manga, on, onChange) {
    const paint = () => {
      btn.classList.toggle("on", on);
      btn.setAttribute("aria-pressed", on);
      btn.title = on ? "Remove bookmark" : "Bookmark (read later)";
      const label = btn.querySelector(".label");
      if (label) label.textContent = on ? "Bookmarked" : "Bookmark";
    };
    paint();
    btn.addEventListener("click", async (e) => {
      e.preventDefault(); e.stopPropagation();   // a card is a link: don't open it
      const next = !on;
      on = next; paint();
      try {
        const res = await fetch("/api/bookmark?" + mangaQuery(author, manga), {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ on: next }),
        });
        if (!res.ok) throw new Error();
        if (onChange) onChange(next);
        refreshBookmarkCount();
      } catch (_) { on = !next; paint(); }
    });
    return { set(value) { on = value; paint(); }, toggle() { btn.click(); } };
  }

  // ---------- manga card (library + bookmarks page) ----------
  function card({ author, manga, name, sub, progress, bookmarked, onBookmark }) {
    const q = mangaQuery(author, manga);
    const box = document.createElement("div");
    box.className = "card";
    box.dataset.name = name.toLowerCase();

    const a = document.createElement("a");
    a.className = "card-link"; a.href = "/manga?" + q;

    const cover = document.createElement("div");
    cover.className = "cover";
    const initial = document.createElement("div");
    initial.className = "initial";
    initial.textContent = (name.trim()[0] || "?").toUpperCase();
    cover.appendChild(initial);
    const img = document.createElement("img");
    img.loading = "lazy"; img.alt = ""; img.src = "/thumb?" + q;
    img.onload = () => initial.remove();
    img.onerror = () => img.remove();
    cover.appendChild(img);
    if (progress > 0) {
      const bar = document.createElement("div");
      bar.className = "progress"; bar.style.width = Math.min(progress, 1) * 100 + "%";
      cover.appendChild(bar);
    }
    a.appendChild(cover);

    const title = document.createElement("div");
    title.className = "name"; title.textContent = name; title.title = name;
    a.appendChild(title);
    if (sub) {
      const s = document.createElement("div");
      s.className = "sub"; s.textContent = sub;
      a.appendChild(s);
    }
    box.appendChild(a);

    // the star sits on top of the cover, next to the link (not inside it)
    const star = document.createElement("button");
    star.type = "button"; star.className = "bm"; star.innerHTML = STAR;
    box.appendChild(star);
    bindBookmark(star, author, manga, !!bookmarked, (on) => { box.classList.toggle("unmarked", !on); if (onBookmark) onBookmark(on); });
    return box;
  }

  document.addEventListener("DOMContentLoaded", refreshBookmarkCount);

  return { $, enc, params, store, mangaQuery, groupKey, getJson, card, bindBookmark, refreshBookmarkCount };
})();