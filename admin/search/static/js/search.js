// Search module: the search box, the filter, the cover grid and ticking galleries.
(() => {
  const { $, api, store, picked, pickedChanged } = Admin;
  let query = null;        // what the current results came from
  let page = 1;
  let shown = [];          // galleries currently in the grid

  const params = () => new URLSearchParams({
    q: query.q, mode: query.mode, hide: query.hide, account: query.account ? "1" : "0", page,
  });

  function card(item) {
    const box = document.createElement("div");
    box.className = "card" + (item.have ? " have" : "") + (picked.has(item.id) ? " selected" : "");
    box.dataset.id = item.id;

    const a = document.createElement("a");
    a.className = "card-link"; a.href = "#"; a.setAttribute("role", "checkbox");
    a.setAttribute("aria-checked", picked.has(item.id));

    const cover = document.createElement("div");
    cover.className = "cover";
    const initial = document.createElement("div");
    initial.className = "initial"; initial.textContent = (item.title.trim()[0] || "?").toUpperCase();
    cover.appendChild(initial);
    if (item.thumb) {
      const img = document.createElement("img");
      img.loading = "lazy"; img.alt = ""; img.src = item.thumb;
      img.onload = () => initial.remove(); img.onerror = () => img.remove();
      cover.appendChild(img);
    }
    if (item.have) {
      const badge = document.createElement("span");
      badge.className = "badge done";
      badge.textContent = item.have === "library" ? "In library" : "Zip waiting";
      cover.appendChild(badge);
    }
    const pick = document.createElement("span");
    pick.className = "pick"; pick.textContent = "✓"; pick.setAttribute("aria-hidden", "true");
    cover.appendChild(pick);
    a.appendChild(cover);

    const name = document.createElement("div");
    name.className = "name"; name.textContent = item.title; name.title = item.title;
    a.appendChild(name);
    const sub = document.createElement("div");
    sub.className = "sub";
    sub.textContent = [item.pages ? item.pages + " pages" : null, item.favorites != null ? "♥ " + item.favorites : null, "#" + item.id]
      .filter(Boolean).join(" · ");
    a.appendChild(sub);

    a.addEventListener("click", (e) => {
      e.preventDefault();
      if (picked.has(item.id)) picked.delete(item.id); else picked.set(item.id, item.title);
      box.classList.toggle("selected", picked.has(item.id));
      a.setAttribute("aria-checked", picked.has(item.id));
      pickedChanged();
    });
    box.appendChild(a);
    return box;
  }

  function message(text) { $("message").replaceChildren(text); $("message").hidden = !text; }

  // ----- the "I am working" signals: top bar, spinner line, button spinner, seconds counter -----
  let run = 0, ticker = null;
  function busy(label, append) {
    const started = Date.now();
    $("loadbar").hidden = false;
    $("search-btn").classList.add("loading"); $("search-btn").textContent = "Searching...";
    $("load-more").classList.add("loading"); $("load-more").disabled = true;
    if (append) $("load-more").textContent = "Loading...";
    clearInterval(ticker);
    const line = document.createElement("div");
    line.className = "busy-line";
    const spin = document.createElement("span"); spin.className = "spinner big";
    const text = document.createElement("span");
    const note = document.createElement("small");
    line.append(spin, text, note);
    if (!append) { $("message").replaceChildren(line); $("message").hidden = false; }
    const tick = () => {
      const s = Math.floor((Date.now() - started) / 1000);
      text.textContent = label + (s ? " " + s + "s" : "");
      note.textContent = s >= 8 ? "Still working. The site limits how fast it can be asked, so this can take a while." : "";
    };
    tick();
    ticker = setInterval(tick, 1000);
  }
  function idle() {
    clearInterval(ticker);
    $("loadbar").hidden = true;
    $("search-btn").classList.remove("loading"); $("search-btn").textContent = "Search";
    $("load-more").classList.remove("loading"); $("load-more").disabled = false; $("load-more").textContent = "Load more";
  }

  async function load(append) {
    const mine = ++run;            // a newer search replaces this one
    busy('Searching "' + query.q + '"...', append);
    if (!append) { $("grid").replaceChildren(); shown = []; $("count").textContent = ""; $("more").hidden = true; $("pick-tools").hidden = true; }
    try {
      const data = await api("/api/search?" + params());
      if (mine !== run) return;
      if (!append) { $("grid").replaceChildren(); shown = []; }
      shown.push(...data.items);
      $("grid").append(...data.items.map(card));
      $("heading").textContent = query.q;
      const extra = data.hidden ? " (" + data.hidden + " hidden by the filter)" : "";
      $("count").textContent = shown.length + " manga" + extra;
      $("pick-tools").hidden = shown.length === 0;
      $("more").hidden = !data.more;
      message(shown.length ? "" : data.hidden ? "Everything on this page was hidden by your filter." : "Nothing found for this search.");
    } catch (error) {
      if (mine !== run) return;
      message(error.message);
    }
    idle();
  }

  $("search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = $("q").value.trim();
    if (!q) { $("q").focus(); return; }
    store.set("hide", $("hide").value); store.set("account", $("account").checked ? "1" : "0"); store.set("mode", $("mode").value);
    query = { q, mode: $("mode").value, hide: $("hide").value, account: $("account").checked };
    page = 1;
    load(false);
  });
  $("load-more").addEventListener("click", () => { page += 1; load(true); });

  $("select-new").addEventListener("click", () => {
    shown.filter((i) => !i.have).forEach((i) => picked.set(i.id, i.title));
    $("grid").querySelectorAll(".card").forEach((c) => c.classList.toggle("selected", picked.has(+c.dataset.id)));
    pickedChanged();
  });
  $("select-none").addEventListener("click", () => {
    picked.clear();
    $("grid").querySelectorAll(".card.selected").forEach((c) => c.classList.remove("selected"));
    pickedChanged();
  });

  // press / to jump to the search box
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") {
      e.preventDefault(); $("q").focus();
    }
  });

  // remembered filter settings + what .env already hides + whether a key is set
  $("hide").value = store.get("hide", "");
  $("account").checked = store.get("account", "1") === "1";
  $("mode").value = store.get("mode", "artist");
  api("/api/status").then((s) => {
    $("zip-folder").textContent = s.folder;
    $("no-key").hidden = s.has_key;
    if (s.hide.length) { $("hide-env").hidden = false; $("hide-env").textContent = "Also hidden from the .env file: " + s.hide.join(", "); }
  }).catch(() => {});
})();
