/* manga.js — one manga: hero, progress, page thumbnails (/manga?a=...&m=...) */
(() => {
  const { $, enc, params, mangaQuery, getJson } = MM;
  const author = params.get("a") || "";
  const manga = params.get("m") || "";
  const query = mangaQuery(author, manga);
  const BATCH = 10;
  let pages = [], shown = 0;

  const readUrl = (page) => "/read?" + query + (page ? "&p=" + page : "");

  const authorHref = "/author?a=" + enc(author);
  $("author-link").href = authorHref;
  $("crumb-author").href = authorHref;
  $("crumb-author").textContent = author || "Library";
  $("author-link").textContent = author;

  // Coming from the library: go back in history so its scroll position and filter are kept
  $("crumb-author").addEventListener("click", (e) => {
    try {
      const from = new URL(document.referrer);
      if (from.origin === location.origin && (from.pathname === "/" || from.pathname === "/author") && history.length > 1) {
        e.preventDefault();
        history.back();
      }
    } catch (_) { /* no referrer: follow the normal link */ }
  });

  function addCards(count) {
    const end = Math.min(shown + count, pages.length);
    const frag = document.createDocumentFragment();
    for (let i = shown; i < end; i++) {
      const a = document.createElement("a");
      a.className = "thumb"; a.href = readUrl(i + 1);
      a.title = "Start reading at page " + (i + 1);

      const box = document.createElement("div");
      box.className = "thumb-box loading";
      if (pages[i].w && pages[i].h) box.style.aspectRatio = pages[i].w + " / " + pages[i].h;
      const img = document.createElement("img");
      img.alt = ""; img.decoding = "async"; img.loading = "lazy";   // "Load all" adds hundreds: only fetch what scrolls into view
      img.onload = () => box.classList.remove("loading");
      img.onerror = () => { box.classList.remove("loading"); img.remove(); };
      img.src = "/pthumb?" + query + "&i=" + i;
      box.appendChild(img);
      if (pages[i].chapter) {
        const tag = document.createElement("span");
        tag.className = "chapter-tag"; tag.textContent = "Chapter " + pages[i].chapter;
        box.appendChild(tag);
      }
      a.appendChild(box);

      const num = document.createElement("div");
      num.className = "num"; num.textContent = i + 1;
      a.appendChild(num);
      frag.appendChild(a);
    }
    $("grid").appendChild(frag);
    shown = end;

    $("more").hidden = shown >= pages.length;
    $("hint").textContent = "Showing " + shown + " of " + pages.length + " pages";
    $("loadall").hidden = pages.length - shown <= BATCH;   // with 10 or fewer left, "Load 10 more" already does it
  }

  const addFact = (fact) => $("facts").appendChild(MM.meta.factItem(fact));

  async function start() {
    const data = await getJson("/api/manga?" + query);
    pages = data.pages;
    const chapters = pages.filter((p) => p.chapter).length;

    // meta.json (when the manga has one) gives the real title, the Japanese title, a few facts and the tags
    const meta = data.meta;
    const title = MM.meta.title(meta, data.title);
    document.title = title;
    $("title").textContent = title;
    $("crumb-title").textContent = title;
    if (meta && meta.japanese && meta.japanese !== title) {
      $("alt-title").textContent = meta.japanese;
      $("alt-title").hidden = false;
    }
    $("cover").src = "/thumb?" + query;
    $("cover").onerror = () => $("cover").remove();

    addFact({ value: String(pages.length), after: " pages" });
    if (chapters) addFact({ value: String(chapters), after: chapters === 1 ? " chapter" : " chapters" });
    MM.meta.facts(meta).forEach(addFact);

    const tags = MM.meta.renderTags(meta);
    if (tags) {
      $("tags").appendChild(tags);
      $("tags-section").hidden = false;
    }

    const saved = data.progress || {};
    const read = $("read");
    if (saved.index > 0) {
      const done = Math.min(saved.index + 1, pages.length);
      read.textContent = "Continue from page " + done;
      read.href = readUrl(done);
      $("restart").hidden = false;
      $("restart").href = readUrl(1);
      $("meter").hidden = false;
      $("meter-text").textContent = done + " / " + pages.length;
      requestAnimationFrame(() => { $("meter-fill").style.width = (done / pages.length) * 100 + "%"; });
    } else {
      read.href = readUrl(1);
    }

    // "Mark as finished" / "Mark as unread" (clears the saved place). Shown only when they would change something.
    const hasProgress = saved.index !== undefined;
    const isFinished = hasProgress && saved.index + 1 >= pages.length;
    $("finish").hidden = isFinished;
    $("reset").hidden = !hasProgress;
    async function setProgress(action, question) {
      if (hasProgress && !confirm(question)) return;
      try {
        const res = await fetch("/api/progress/" + action + "?" + query, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
        });
        if (!res.ok) throw new Error();
        location.reload();
      } catch (_) { alert("Could not save. Is read mode still running in the terminal?"); }
    }
    $("finish").onclick = () => setProgress("finish", "Mark \"" + title + "\" as finished? Your saved page will be replaced.");
    $("reset").onclick = () => setProgress("reset", "Mark \"" + title + "\" as unread? Your saved page will be forgotten. Bookmarks are kept.");

    // "Go to bookmark" opens the reader on the marked page; it follows the bookmark as it changes
    const showMark = (mark) => {
      $("goto-mark").hidden = !mark || !mark.page;
      if (mark && mark.page) $("goto-mark").href = readUrl(mark.page);
    };
    showMark(data.bookmarked);
    MM.bindBookmark($("bookmark"), author, manga, data.bookmarked, showMark);

    $("hero").hidden = false;
    $("pages-section").hidden = false;
    $("pages-count").textContent = pages.length;
    addCards(BATCH);
  }

  MM.shortcuts([["/", "Search all manga"]]);
  $("load10").onclick = () => addCards(BATCH);
  $("loadall").onclick = () => addCards(pages.length);
  start().catch(() => {
    $("crumb-title").textContent = "Not found";
    $("msg").innerHTML = "<strong>Could not load this manga</strong>Is read mode still running in the terminal?";
    $("msg").hidden = false;
  });
})();