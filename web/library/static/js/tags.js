/* tags.js — the tag filter panel on the library and author pages (MM.tagPanel)
 *
 * It lists the tags of the manga that are loaded, with how many manga have each, and lets you click them.
 * It never keeps a filter of its own: a click only edits the search box (see setTag in meta.js), so the box,
 * the URL (/?q=...) and the panel always agree.
 *   click once: must have the tag   click again: must NOT have it   click a third time: forget it
 */
MM.tagPanel = ({ input, cards, loaded, onChange }) => {
  const { $, store } = MM;
  const M = MM.meta;
  const button = $("tags-toggle"), panel = $("tagpanel"), find = $("tag-find");
  const typesEl = $("tag-types"), list = $("tag-list"), note = $("tag-note"), clear = $("tag-clear"), badge = $("tags-n");
  const LIMIT = 80;                         // chips drawn at once; the box above finds the rest
  let open = false, typeFilter = "all", index = null;

  const rank = (type) => (M.TYPE_ORDER.includes(type) ? M.TYPE_ORDER.indexOf(type) : M.TYPE_ORDER.length);
  const typeName = (type) => M.TYPE_LABEL[type] || type;

  // [{type, label, key, count}] most common first
  function buildIndex() {
    const map = new Map();
    for (const card of cards()) {
      for (const t of card.doc.tags) {
        const id = t.type + "\u0000" + t.key;
        let entry = map.get(id);
        if (!entry) map.set(id, (entry = { type: t.type, label: t.label, key: t.key, count: 0 }));
        entry.count++;
      }
    }
    return [...map.values()].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  }

  function paintTypes() {
    const counts = new Map();
    index.forEach((e) => counts.set(e.type, (counts.get(e.type) || 0) + 1));
    const kinds = [...counts.keys()].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
    if (typeFilter !== "all" && !counts.has(typeFilter)) typeFilter = "all";
    typesEl.replaceChildren(...[["all", "All", index.length], ...kinds.map((k) => [k, typeName(k), counts.get(k)])].map(([key, label, n]) => {
      const chip = document.createElement("button");
      chip.type = "button"; chip.className = "chip small"; chip.dataset.type = key;
      chip.setAttribute("aria-pressed", key === typeFilter);
      chip.textContent = label + " " + n;
      return chip;
    }));
  }

  function paintList() {
    const needle = M.norm(find.value).trim();
    const stateOf = M.tagStates(input.value);
    const pool = index.filter((e) => (typeFilter === "all" || e.type === typeFilter) && (!needle || e.key.includes(needle)));
    const keep = list.scrollTop;
    list.replaceChildren(...pool.slice(0, LIMIT).map((e) => {
      const chip = document.createElement("button");
      chip.type = "button"; chip.className = "tagchip";
      const state = stateOf(e.type, e.label);
      if (state) chip.dataset.state = state;
      chip.setAttribute("aria-pressed", state === "in" ? "true" : state === "out" ? "mixed" : "false");
      chip.title = state === "in" ? "Must have this tag. Click to exclude it instead."
        : state === "out" ? "Must NOT have this tag. Click to clear."
        : "Click to show only manga with this tag.";
      if (typeFilter === "all" && e.type !== "tag") {
        const kind = document.createElement("span");
        kind.className = "kind"; kind.textContent = e.type;
        chip.appendChild(kind);
      }
      const name = document.createElement("span");
      name.className = "label"; name.textContent = e.label;
      const n = document.createElement("span");
      n.className = "n"; n.textContent = e.count;
      chip.append(name, n);
      chip._entry = e;
      return chip;
    }));
    list.scrollTop = keep;
    note.textContent = !loaded() && !index.length ? "Loading..."
      : !pool.length ? (index.length ? "No tag matches." : "No manga here have tags yet: they come from each manga's meta.json.")
      : pool.length > LIMIT ? "Showing the " + LIMIT + " most common of " + pool.length + ". Type in the box to find others." : "";
  }

  function paint() {
    if (!index) index = buildIndex();
    paintTypes();
    paintList();
  }

  // called after every search / data change: keeps the little counter right, and the panel in step when it is open
  function update() {
    const n = M.tagTermCount(input.value);
    badge.textContent = n; badge.hidden = n === 0;
    clear.hidden = n === 0;
    if (open) paint();
  }

  function setOpen(next) {
    open = next;
    panel.hidden = !open;
    button.setAttribute("aria-expanded", open);
    store.set("library-tagpanel", open ? "1" : "0");
    if (open) paint();
  }

  list.addEventListener("click", (e) => {
    const chip = e.target.closest(".tagchip");
    if (!chip) return;
    const entry = chip._entry;
    const now = M.tagState(input.value, entry.type, entry.label);
    const next = now === null ? "in" : now === "in" ? "out" : null;      // none -> must have -> must not have -> none
    input.value = M.setTag(input.value, entry.type, entry.label, next);
    onChange();
  });
  typesEl.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-type]");
    if (!chip) return;
    typeFilter = chip.dataset.type;
    paint();
  });
  find.addEventListener("input", paintList);
  find.addEventListener("keydown", (e) => { if (e.key === "Escape") { find.value = ""; paintList(); e.stopPropagation(); find.blur(); } });
  clear.addEventListener("click", () => { input.value = M.clearTags(input.value); onChange(); });
  button.addEventListener("click", () => setOpen(!open));

  if (store.get("library-tagpanel") === "1") setOpen(true);
  return { update, toggle: () => setOpen(!open), invalidate: () => { index = null; } };
};
