/* reader.js — the reader (/read?a=...&m=...&p=...), page mode + scroll mode */
(() => {
  const { $, params, store, mangaQuery, getJson } = MM;
  const bar = $("bar"), pagesEl = $("pages"), select = $("chapters");
  const query = mangaQuery(params.get("a"), params.get("m"));
  const WIDTH_STEP = 100, WIDTH_MIN = 400, WIDTH_MAX = 2400;
  let pages = [], els = [], chapters = [], current = 0, saveTimer = null;
  let paged = true, fitWidth = false;

  /* ---------- width ---------- */
  let width = parseInt(store.get("reader-width"), 10) || 800;
  function applyWidth() {
    width = Math.max(WIDTH_MIN, Math.min(width, WIDTH_MAX));
    document.documentElement.style.setProperty("--w", width + "px");
    store.set("reader-width", width);
  }
  function setWidth(next) {
    if (paged) { width = next; applyWidth(); return; }
    const keep = currentPosition();
    width = next; applyWidth();
    scrollToPosition(keep.index, keep.fraction);
  }

  /* ---------- build ---------- */
  function build(data) {
    pages = data.pages;
    $("title").textContent = data.title;
    document.title = data.title;

    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) { load(entry.target); observer.unobserve(entry.target); }
      }
    }, { rootMargin: "2500px 0px" });

    pages.forEach((page, i) => {
      if (page.chapter) {
        const label = document.createElement("div");
        label.className = "chapter-label";
        label.textContent = "Chapter " + page.chapter;
        pagesEl.appendChild(label);
        chapters.push({ label: "Chapter " + page.chapter, index: i });
      }
      const box = document.createElement("div");
      box.className = "leaf";
      box.dataset.i = i;
      if (page.w && page.h) box.style.aspectRatio = page.w + " / " + page.h;
      pagesEl.appendChild(box);
      els.push(box);
      observer.observe(box);
    });

    if (!chapters.length) chapters.push({ label: "Start", index: 0 });
    else if (chapters[0].index > 0) chapters.unshift({ label: "Start", index: 0 });

    chapters.forEach((c, n) => {
      const option = document.createElement("option");
      option.value = n; option.textContent = c.label;
      select.appendChild(option);
    });

    const end = document.createElement("div");
    end.className = "end";
    const text = document.createElement("div");
    text.textContent = "End of " + data.title;
    const top = document.createElement("button");
    top.className = "btn ghost"; top.type = "button"; top.textContent = "Back to top";
    top.onclick = () => window.scrollTo({ top: 0 });
    end.append(text, top);
    pagesEl.appendChild(end);
  }

  function load(box) {
    if (box.firstChild) return Promise.resolve();
    return new Promise((resolve) => {
      const img = document.createElement("img");
      img.alt = "Page " + (+box.dataset.i + 1);
      img.decoding = "async";
      img.onload = img.onerror = () => { box.classList.add("loaded"); box.style.aspectRatio = ""; resolve(); };
      img.src = imgUrl(box.dataset.i);
      box.appendChild(img);
    });
  }

  /* ---------- position ---------- */
  function currentPosition() {
    const line = window.innerHeight * 0.3;
    let index = current;
    // walk from the last known page, cheap on long folders
    while (index > 0 && els[index].getBoundingClientRect().top > line) index--;
    while (index < els.length - 1 && els[index].getBoundingClientRect().bottom <= line) index++;
    const rect = els[index].getBoundingClientRect();
    const fraction = rect.height ? Math.max(0, Math.min((line - rect.top) / rect.height, 1)) : 0;
    return { index, fraction };
  }

  function scrollToPosition(index, fraction = 0) {
    const box = els[index];
    if (!box) return;
    const line = window.innerHeight * 0.3;  // same reference line as currentPosition()
    window.scrollTo({ top: box.getBoundingClientRect().top + window.scrollY + box.offsetHeight * fraction - line });
  }

  function goToChapter(n) {
    n = Math.max(0, Math.min(n, chapters.length - 1));
    if (paged) { showPage(chapters[n].index); return; }
    const box = els[chapters[n].index];
    // land on the chapter label when there is one
    const label = box.previousElementSibling;
    const target = label && label.className === "chapter-label" ? label : box;
    window.scrollTo({ top: target.getBoundingClientRect().top + window.scrollY - 48 });
  }

  function chapterOf(index) {
    let n = 0;
    chapters.forEach((c, k) => { if (c.index <= index) n = k; });
    return n;
  }

  function onScroll() {
    if (paged) return;
    const pos = currentPosition();
    current = pos.index;
    $("counter").textContent = (current + 1) + " / " + pages.length;
    select.value = chapterOf(current);
    const max = document.documentElement.scrollHeight - window.innerHeight;
    $("progress").style.width = (max > 0 ? (window.scrollY / max) * 100 : 0) + "%";

    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => save(pos), 700);
  }

  function save(pos) {
    fetch("/api/progress?" + query, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index: pos.index, fraction: pos.fraction }),
      keepalive: true,
    }).catch(() => {});
  }

  /* ---------- top bar: hide while reading down, show when scrolling up ---------- */
  let lastY = 0, barLocked = false;
  function updateBar() {
    if (paged) return;
    const y = window.scrollY;
    if (!barLocked) {
      if (y < 60 || y < lastY - 4) bar.classList.remove("hidden");
      else if (y > lastY + 4) bar.classList.add("hidden");
    }
    lastY = y;
  }
  document.addEventListener("mousemove", (e) => {
    if (barLocked) return;
    if (e.clientY < 50) bar.classList.remove("hidden");
    else if (paged && e.clientY > 110) bar.classList.add("hidden");
  });

  let ticking = false;
  window.addEventListener("scroll", () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { onScroll(); updateBar(); ticking = false; });
  }, { passive: true });

  /* ---------- page-by-page mode ---------- */
  const viewerImg = $("page-img");
  const imgUrl = (i) => "/img?" + query + "&i=" + i;

  function showPage(i) {
    i = Math.max(0, Math.min(i, pages.length - 1));
    current = i;
    viewerImg.src = imgUrl(i);
    window.scrollTo(0, 0);
    // warm the cache for the pages around this one
    [i + 1, i + 2, i - 1].forEach((k) => { if (k >= 0 && k < pages.length) new Image().src = imgUrl(k); });

    $("counter").textContent = (i + 1) + " / " + pages.length;
    select.value = chapterOf(i);
    $("progress").style.width = ((i + 1) / pages.length) * 100 + "%";
    document.title = $("title").textContent + " · " + (i + 1) + "/" + pages.length;

    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => save({ index: i, fraction: 0 }), 500);
  }

  const step = (d) => showPage(current + d);

  // click the left half of a page to go back, the right half to go forward
  $("viewer").addEventListener("click", (e) => {
    if (!paged || e.button !== 0) return;
    step(e.clientX < window.innerWidth / 2 ? -1 : 1);
  });

  async function setMode(wantPaged) {
    paged = wantPaged;
    store.set("reader-mode", paged ? "paged" : "scroll");
    document.body.classList.toggle("paged", paged);
    $("mode").textContent = paged ? "Page" : "Scroll";
    if (paged) {
      bar.classList.add("hidden");
      showPage(current);
    } else {
      bar.classList.remove("hidden");
      document.title = $("title").textContent;
      await Promise.all(els.slice(0, current + 1).map(load));
      scrollToPosition(current, 0);
      onScroll();
    }
  }

  function setFit(wantWidth) {
    fitWidth = wantWidth;
    store.set("reader-fit", fitWidth ? "width" : "screen");
    document.body.classList.toggle("fitwidth", fitWidth);
    $("fit").textContent = fitWidth ? "Width" : "Screen";
    window.scrollTo(0, 0);
  }

  /* ---------- controls ---------- */
  function isAtChapterStart() {
    const atStart = chapters[chapterOf(current)].index === current;
    return paged ? atStart : atStart && currentPosition().fraction < 0.1;
  }
  function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen().catch(() => {});
  }

  select.onchange = () => goToChapter(+select.value);
  $("prev").onclick = () => goToChapter(chapterOf(current) - (isAtChapterStart() ? 1 : 0));
  $("next").onclick = () => goToChapter(chapterOf(current) + 1);
  $("narrower").onclick = () => setWidth(width - WIDTH_STEP);
  $("wider").onclick = () => setWidth(width + WIDTH_STEP);
  $("fs").onclick = toggleFullscreen;
  $("mode").onclick = () => setMode(!paged);
  $("fit").onclick = () => setFit(!fitWidth);

  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey || e.target === select) return;
    if (paged) {
      const forward = { ArrowRight: 1, PageDown: 1, " ": e.shiftKey ? -1 : 1 };
      const back = { ArrowLeft: -1, PageUp: -1 };
      const d = e.key in forward ? forward[e.key] : back[e.key];
      if (d) { step(d); e.preventDefault(); return; }
      if (e.key === "Home") { showPage(0); e.preventDefault(); return; }
      if (e.key === "End") { showPage(pages.length - 1); e.preventDefault(); return; }
    }
    switch (e.key) {
      case "m": $("mode").click(); break;
      case "w": $("fit").click(); break;
      case "n": case "]": $("next").click(); break;
      case "p": case "[": $("prev").click(); break;
      case "+": case "=": $("wider").click(); break;
      case "-": case "_": $("narrower").click(); break;
      case "f": toggleFullscreen(); break;
      case "h": barLocked = !barLocked; bar.classList.toggle("hidden", barLocked); break;
      default: return;
    }
    e.preventDefault();
  });

  /* ---------- start ---------- */
  applyWidth();
  paged = store.get("reader-mode") !== "scroll";
  fitWidth = store.get("reader-fit") === "width";
  document.body.classList.toggle("paged", paged);
  document.body.classList.toggle("fitwidth", fitWidth);
  $("mode").textContent = paged ? "Page" : "Scroll";
  $("fit").textContent = fitWidth ? "Width" : "Screen";
  if (paged) bar.classList.add("hidden");

  getJson("/api/manga?" + query).then(async (data) => {
    build(data);
    const saved = data.progress || {};
    // ?p=N (from the manga page) wins over the saved position
    const wanted = parseInt(params.get("p"), 10);
    const index = Math.min(wanted > 0 ? wanted - 1 : (saved.index || 0), els.length - 1);
    if (wanted > 0) saved.fraction = 0;
    if (paged) { showPage(index); return; }
    if (index > 0) {
      // load the pages above the saved spot first so the position is exact
      await Promise.all(els.slice(0, index + 1).map(load));
      scrollToPosition(index, saved.fraction || 0);
    }
    onScroll();
    lastY = window.scrollY;
  }).catch(() => {
    pagesEl.innerHTML = '<div class="msg">Could not load this manga. Is the reader still running in the terminal?</div>';
  });
})();
