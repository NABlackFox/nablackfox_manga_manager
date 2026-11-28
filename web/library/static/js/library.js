/* library.js — authors page (/) and one author's manga (/author?a=...) */
(() => {
  const { $, enc, params, groupKey, getJson } = MM;
  const author = params.get("a");

  // "All" / "Unread" / "In progress" / "Finished": remembered between visits
  const STATUSES = ["all", "unread", "reading", "done"];
  let status = STATUSES.includes(MM.store.get("library-status")) ? MM.store.get("library-status") : "all";
  const isFiltering = () => $("search").value.trim() !== "" || status !== "all";

  // ---------- cards ----------
  // "48 pages · ♥ 13.5K · page 12": favorites come from meta.json, so only manga that have one show them
  const cardSub = (m) => [
    m.pages + " pages",
    m.meta && m.meta.favorites !== undefined ? "♥ " + MM.meta.compact(m.meta.favorites) : "",
    m.read ? "page " + m.read : "",
  ].filter(Boolean).join(" · ");

  const mangaCards = (authorName, manga) => manga.map((m) => MM.card({
    author: authorName,
    manga: m.name,
    name: m.name,
    meta: m.meta,
    pages: m.pages,
    sub: cardSub(m),
    progress: m.read / m.pages,
    bookmarked: m.bookmarked,
    onBookmark: (mark) => {          // keep the cached library in step, so a reload shows the right star
      m.bookmarked = mark;
      if (shownData) writeCache(shownData);
    },
  }));

  // ---------- sections ----------
  // One section = one author name followed by that author's manga.
  // On an author page there is a single section with no heading.
  let sections = [];
  let letterLinks = new Map();   // letter -> link in the letter bar
  let runId = 0;                 // bumped on every (re)load so stale fetches are ignored

  const letterOrder = (a, b) => (a === "#" ? 0 : 1) - (b === "#" ? 0 : 1) || (a < b ? -1 : a > b ? 1 : 0);
  const sortAuthors = (list) => list.sort((a, b) =>
    letterOrder(groupKey(a.name), groupKey(b.name))
    || a.name.localeCompare(b.name, undefined, { sensitivity: "base", numeric: true }));

  function makeSection(title, href) {
    const el = document.createElement("section");
    el.className = "group";
    const count = document.createElement("span");
    count.className = "n";
    const grid = document.createElement("div");
    grid.className = "grid";
    if (title !== null) {
      const head = document.createElement("h2");
      head.className = "group-head";
      const link = document.createElement("a");
      link.href = href; link.textContent = title; link.title = "Open " + title;
      head.append(link, count);
      el.append(head);
    }
    el.append(grid);

    // "Show more" row (authors page only): one row of manga by default
    const sec = { el, grid, count, cards: [], loaded: false, expanded: false, title: title || "", key: groupKey(title || "") };
    if (title !== null) {
      const toggle = document.createElement("button");
      toggle.type = "button"; toggle.className = "toggle"; toggle.hidden = true;
      toggle.addEventListener("click", () => { sec.expanded = !sec.expanded; applyCollapse(sec); });
      el.append(toggle);
      sec.toggle = toggle;
    }
    return sec;
  }

  function fillSection(sec, authorName, manga) {
    sec.cards = mangaCards(authorName, manga);
    sec.grid.append(...sec.cards);
    sec.loaded = true;
    if (tagPanel) tagPanel.invalidate();
  }

  function mount(list) {
    const y = window.scrollY;          // rebuilding the page must not throw you back to the top
    sections = list;
    if (tagPanel) tagPanel.invalidate();
    $("groups").replaceChildren(...list.map((sec) => sec.el));
    window.scrollTo(0, y);
  }

  // ---------- one row per author, with "Show more" ----------
  const columnCount = (grid) => getComputedStyle(grid).gridTemplateColumns.split(" ").length;

  function applyCollapse(sec) {
    if (!sec.toggle || !sec.loaded || sec.el.hidden) return;
    const filtering = isFiltering();
    const matches = sec.cards.filter((c) => !c.hidden);
    const cols = columnCount(sec.grid);
    const collapse = !filtering && !sec.expanded;
    matches.forEach((c, i) => c.classList.toggle("clipped", collapse && i >= cols));

    const extra = matches.length - cols;
    sec.toggle.hidden = filtering || extra <= 0;      // while filtering, everything that matches is shown
    sec.toggle.textContent = sec.expanded ? "Show less" : "Show " + extra + " more";
    sec.toggle.setAttribute("aria-expanded", sec.expanded);
  }

  let resizeTimer = null;
  window.addEventListener("resize", () => {           // the number of columns changes with the window
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => sections.forEach(applyCollapse), 120);
  });

  // the "Continue reading" row is for browsing: hidden while searching or filtering, and when empty
  const updateRecent = () => { $("recent").hidden = isFiltering() || !$("rail").children.length; };

  // ---------- filter + counts ----------
  // The search box understands words, tag:name, -tag:name, artist:, pages:>30 ... (see the top of meta.js).
  // Every card carries what is searched (c.doc: folder name, titles, author, tags ...).
  function render() {
    const query = MM.meta.parse($("search").value);
    let shown = 0, total = 0;
    const letterHasMatch = new Set();

    for (const sec of sections) {
      let visible = 0;
      for (const c of sec.cards) {
        const match = MM.meta.matches(query, c.doc)
          && (status === "all" || c.dataset.status === status);
        c.hidden = !match;
        if (match) visible++;
      }
      shown += visible;
      total += sec.cards.length;
      sec.el.hidden = sec.loaded && visible === 0;   // empty authors / no match: hide
      sec.count.textContent = !sec.loaded ? "loading..." : isFiltering() ? visible + " / " + sec.cards.length : sec.cards.length;
      if (visible > 0) letterHasMatch.add(sec.key);
    }
    sections.forEach(applyCollapse);
    const allLoaded = sections.every((s) => s.loaded);
    for (const [k, link] of letterLinks) link.classList.toggle("off", !letterHasMatch.has(k) && allLoaded);

    const loading = !allLoaded;
    $("empty").textContent = isFiltering() ? "Nothing matches." : "No manga found.";
    $("empty").hidden = shown > 0 || loading;
    $("count").textContent = (isFiltering() ? shown + " / " + total : total) + " manga" + (loading ? " ..." : "");
    updateRecent();
    if (tagPanel) tagPanel.update();
  }

  let queued = false;
  function renderSoon() {            // many authors finish loading at once: draw once per frame
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; render(); });
  }

  // ---------- remembered state ----------
  // Library data is cached in localStorage and shown instantly; a fresh copy is fetched in
  // the background and the page is only rebuilt if something changed (e.g. reading progress).
  // The scroll position is remembered per tab in sessionStorage.
  const CACHE_KEY = "library-cache-v3";            // v3: manga carry their meta.json information
  try { localStorage.removeItem("library-cache-v2"); } catch (_) {}
  const SCROLL_KEY = "scroll:" + location.pathname + location.search;

  function readCache() {
    try {
      const data = JSON.parse(localStorage.getItem(CACHE_KEY));
      return Array.isArray(data) ? data : null;
    } catch (_) { return null; }
  }
  function writeCache(data) { MM.store.set(CACHE_KEY, JSON.stringify(data)); }
  function saveScroll() {
    try { sessionStorage.setItem(SCROLL_KEY, String(Math.round(window.scrollY))); } catch (_) {}
  }
  function restoreScroll() {
    try {
      const y = Number(sessionStorage.getItem(SCROLL_KEY));
      if (y > 0) window.scrollTo(0, y);
    } catch (_) {}
  }
  history.scrollRestoration = "manual";   // restored by hand, after the content exists
  window.addEventListener("pagehide", saveScroll);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") saveScroll(); });

  // ---------- letter bar ----------
  function buildLetterBar() {
    const jump = $("jump");
    jump.replaceChildren();
    letterLinks = new Map();
    const letters = [...new Set(sections.map((sec) => sec.key))].sort(letterOrder);
    for (const k of letters) {
      const link = document.createElement("a");
      link.href = "#"; link.textContent = k;
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const target = sections.find((sec) => sec.key === k && !sec.el.hidden);
        if (!target) return;
        const offset = $("jump").getBoundingClientRect().bottom + 12;
        window.scrollTo({ top: window.scrollY + target.el.getBoundingClientRect().top - offset, behavior: "smooth" });
      });
      jump.appendChild(link);
      letterLinks.set(k, link);
    }
    jump.hidden = false;
  }

  // ---------- loading the whole library ----------
  // What is on screen right now: [{name, manga: [{name, pages, read}]}]
  let shownData = null;

  function showData(data) {
    shownData = data;
    mount(data.map((a) => {
      const sec = makeSection(a.name, "/author?a=" + enc(a.name));
      fillSection(sec, a.name, a.manga);
      return sec;
    }));
    buildLetterBar();
    render();
  }

  // onList(data) / onAuthor(i) let the first-ever load fill in progressively.
  async function fetchAll(id, onList, onAuthor) {
    const authors = await getJson("/api/library");
    if (id !== runId) return null;
    const data = sortAuthors(authors).map((a) => ({ name: a.name, manga: [] }));
    if (onList) onList(data);

    let next = 0, complete = true;
    const gone = new Set();             // authors deleted while we were loading
    const worker = async () => {
      while (next < data.length) {
        const i = next++;
        try {
          data[i].manga = (await getJson("/api/author?a=" + enc(data[i].name))).manga;
          if (id !== runId) return;
        } catch (err) {
          if (err.status === 404) gone.add(i);
          else complete = false;        // a failed author: never cache a partial library
        }
        if (onAuthor) onAuthor(i);
      }
    };
    await Promise.all(Array.from({ length: 6 }, worker));
    return id === runId ? { data: data.filter((_, i) => !gone.has(i)), complete } : null;
  }

  // Fetch fresh data quietly; rebuild the page (keeping the scroll position) only if it changed.
  async function revalidate(id) {
    const res = await fetchAll(id);
    if (!res) return;
    if (res.complete) writeCache(res.data);
    if (JSON.stringify(res.data) !== JSON.stringify(shownData)) showData(res.data);
  }

  async function loadLibrary(id) {
    document.title = "Library";
    const cached = readCache();
    if (cached) {                       // instant: no loading, back where you were
      showData(cached);
      restoreScroll();
      return revalidate(id);
    }

    // very first visit: no cache yet, so fill the sections in as they arrive
    let live = null;
    const res = await fetchAll(
      id,
      (data) => {
        live = data;
        mount(data.map((a) => makeSection(a.name, "/author?a=" + enc(a.name))));
        buildLetterBar();
        render();
      },
      (i) => { fillSection(sections[i], live[i].name, live[i].manga); renderSoon(); }
    );
    if (!res) return;
    shownData = res.data;
    if (res.complete) writeCache(res.data);
    render();
    restoreScroll();
  }

  async function loadAuthor(id) {
    let data;
    try { data = await getJson("/api/author?a=" + enc(author)); }
    catch (_) {
      $("heading").textContent = "Author not found";
      $("empty").textContent = "That author folder no longer exists.";
      $("empty").hidden = false;
      return;
    }
    if (id !== runId) return;
    document.title = data.name;
    $("heading").textContent = data.name;
    $("crumbs").hidden = false;
    $("crumb-author").textContent = data.name;

    const sec = makeSection(null);
    fillSection(sec, data.name, data.manga);
    mount([sec]);
    render();
    restoreScroll();
  }

  // ---------- continue reading ----------
  // The manga you are in the middle of, newest first. Clicking one resumes at the exact place you stopped.
  async function loadRecent() {
    try {
      const items = await getJson("/api/recent");
      $("rail").replaceChildren(...items.map((m) => MM.card({
        author: m.author,
        manga: m.name,
        name: m.name,
        meta: m.meta,
        pages: m.pages,
        sub: m.author + " · page " + m.read + " / " + m.pages,
        progress: m.read / m.pages,
        bookmarked: m.bookmarked,
        href: "/read?" + MM.mangaQuery(m.author, m.name),
      })));
    } catch (_) { $("rail").replaceChildren(); }
    updateRecent();
  }

  function start() {
    const id = ++runId;
    if (author === null) loadRecent();
    return author === null ? loadLibrary(id) : loadAuthor(id);
  }

  // ---------- filter chips, random ----------
  const chips = [...document.querySelectorAll(".chip[data-status]")];
  function paintChips() { chips.forEach((c) => c.setAttribute("aria-pressed", c.dataset.status === status)); }
  paintChips();
  chips.forEach((c) => c.addEventListener("click", () => {
    status = c.dataset.status;
    MM.store.set("library-status", status);
    paintChips();
    render();
  }));

  function openRandom() {
    const pool = sections.filter((s) => !s.el.hidden).flatMap((s) => s.cards.filter((c) => !c.hidden));
    if (!pool.length) return;
    location.href = pool[Math.floor(Math.random() * pool.length)].querySelector(".card-link").href;
  }
  $("random").addEventListener("click", openRandom);

  // ---------- tag filter panel ----------
  // It reads the cards that are loaded and edits the search box, so the search box stays the one place the filter lives.
  const tagPanel = MM.tagPanel({
    input: $("search"),
    cards: () => sections.flatMap((s) => s.cards),
    loaded: () => sections.length > 0 && sections.every((s) => s.loaded),
    onChange: render,
  });

  // ---------- events ----------
  $("search").value = params.get("q") || "";     // /?q=... comes from the search box on other pages and from tags
  $("search").addEventListener("input", render);
  // Enter with exactly one match opens it
  $("search").addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const hits = sections.flatMap((s) => s.el.hidden ? [] : s.cards.filter((c) => !c.hidden));
    if (hits.length === 1) location.href = hits[0].querySelector(".card-link").href;
  });
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName);
    if (e.key === "/" && !typing) { e.preventDefault(); $("search").focus(); }
    else if (e.key === "Escape") { $("search").value = ""; $("search").blur(); render(); }
    else if (e.key === "r" && !typing) openRandom();
    else if (e.key === "t" && !typing) tagPanel.toggle();
  });
  MM.shortcuts([["/", "Search manga, authors and tags"], ["Enter", "Open the match (when only one is left)"],
    ["Esc", "Clear the search"], ["r", "Open a random manga from what is shown"], ["t", "Show / hide the tag filter"],
    ...MM.meta.searchHelp]);
  // back from the reader: refresh reading progress
  window.addEventListener("pageshow", (e) => {
    if (!e.persisted) return;
    if (author === null) { loadRecent(); revalidate(++runId); } else start();
  });

  start().catch(() => {
    $("empty").textContent = "Could not load. Is read mode still running in the terminal?";
    $("empty").hidden = false;
  });
})();