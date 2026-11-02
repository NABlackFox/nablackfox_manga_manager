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
      img.alt = ""; img.decoding = "async";
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
    $("load50").hidden = pages.length - shown <= BATCH;
  }

  function addFact(html) {
    const li = document.createElement("li");
    li.innerHTML = html;
    $("facts").appendChild(li);
  }

  async function start() {
    const data = await getJson("/api/manga?" + query);
    pages = data.pages;
    const chapters = pages.filter((p) => p.chapter).length;

    document.title = data.title;
    $("title").textContent = data.title;
    $("crumb-title").textContent = data.title;
    $("cover").src = "/thumb?" + query;
    $("cover").onerror = () => $("cover").remove();

    addFact("<b>" + pages.length + "</b> pages");
    if (chapters) addFact("<b>" + chapters + "</b> " + (chapters === 1 ? "chapter" : "chapters"));

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

    $("hero").hidden = false;
    $("pages-section").hidden = false;
    $("pages-count").textContent = pages.length;
    addCards(BATCH);
  }

  $("load10").onclick = () => addCards(BATCH);
  $("load50").onclick = () => addCards(50);
  start().catch(() => {
    $("crumb-title").textContent = "Not found";
    $("msg").innerHTML = "<strong>Could not load this manga</strong>Is read mode still running in the terminal?";
    $("msg").hidden = false;
  });
})();
