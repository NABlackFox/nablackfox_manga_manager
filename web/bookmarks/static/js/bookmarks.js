/* bookmarks.js — the Bookmarks page (/bookmarks): manga you plan to read next */
(() => {
  const { $, getJson } = MM;
  let cards = [];

  function updateCount() {
    const left = cards.filter((c) => !c.classList.contains("unmarked")).length;
    $("count").textContent = left + " manga";
  }

  async function start() {
    const items = await getJson("/api/bookmarks");
    cards = items.map((m) => MM.card({
      author: m.author,
      manga: m.name,
      name: m.name,
      meta: m.meta,
      pages: m.pages,
      sub: m.author + " · " + m.pages + " pages" + (m.read ? " · page " + m.read : ""),
      progress: m.read / m.pages,
      bookmarked: m.bookmarked,
      readAtMark: true,              // a bookmark opens the reader on the marked page
      onBookmark: updateCount,       // un-starred cards stay (dimmed) until you reload, so a slip can be undone
    }));
    $("grid").replaceChildren(...cards);
    updateCount();
    $("empty").hidden = items.length > 0;
    $("grid").hidden = items.length === 0;
  }

  // same search language as the library: words, tag:name, -tag:name, artist:, pages:>30 ... (see meta.js)
  $("search").addEventListener("input", () => {
    const query = MM.meta.parse($("search").value);
    cards.forEach((c) => { c.hidden = !MM.meta.matches(query, c.doc); });
  });
  MM.shortcuts([["/", "Filter bookmarks"], ["Esc", "Clear the filter"], ...MM.meta.searchHelp]);
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== $("search")) { e.preventDefault(); $("search").focus(); }
    else if (e.key === "Escape") { $("search").value = ""; $("search").blur(); $("search").dispatchEvent(new Event("input")); }
  });

  start().catch(() => {
    $("empty").innerHTML = "<strong>Could not load</strong>Is read mode still running in the terminal?";
    $("empty").hidden = false;
  });
})();