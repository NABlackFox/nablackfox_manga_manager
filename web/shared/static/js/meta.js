/* meta.js — what meta.json adds to the pages (exposed as MM.meta). Load it after common.js.
 *
 * 1. Search: one small query language used by the library, the author pages and the bookmarks page.
 * 2. Display: titles, facts and tag lists, so every page shows the gallery information the same way.
 *
 * The values come from a file downloaded from the internet, so they are only ever put on the page as
 * text (textContent), never as HTML.
 *
 * Search language (words are separated by spaces, all of them must match):
 *   glasses                 a word found in the title, author, scanlator, id or any tag
 *   "big breasts"           a phrase, in quotes
 *   tag:glasses             has a tag containing "glasses" (any kind of tag)    tag:"glasses" = exactly that tag
 *   artist:  group:  parody:  character:  language:  category:    the same, limited to that kind of tag
 *   -tag:ahegao  -glasses   NOT: a minus in front of anything
 *   title:  author:  scanlator:            search only that field
 *   pages:>30  pages:20-40  favorites:>=1k  year:2021  id:374818     numbers: > >= < <= = or a-b, k = thousand
 *   has:meta   -has:meta    with / without a meta.json
 * Anything else (including a prefix that is not in this list, such as "re:zero") is an ordinary word.
 * A half-typed term such as "tag:" or "pages:>" is ignored until it is complete, so the list never flashes empty.
 */
(() => {
  const MM = window.MM;
  const enc = encodeURIComponent;

  // ---------- tag kinds ----------
  // The kinds that nhentai uses, in the order they are shown on a manga page.
  const TYPE_ORDER = ["artist", "group", "parody", "character", "category", "language", "tag"];
  const TYPE_LABEL = {
    artist: "Artists", group: "Groups", parody: "Parodies", character: "Characters",
    category: "Categories", language: "Languages", tag: "Tags",
  };
  // search prefix -> kind of tag ("tag" is the generic one: it looks at every kind)
  const TAG_FIELDS = {
    tag: "tag", tags: "tag",
    artist: "artist", artists: "artist",
    group: "group", circle: "group",
    parody: "parody", series: "parody",
    character: "character", char: "character",
    language: "language", lang: "language",
    category: "category", cat: "category",
  };
  const TEXT_FIELDS = { title: "title", name: "title", author: "author", scanlator: "scanlator" };
  const NUMBER_FIELDS = { pages: "pages", favorites: "favorites", favs: "favorites", likes: "favorites", year: "year", id: "id" };
  const isField = (f) => f in TAG_FIELDS || f in TEXT_FIELDS || f in NUMBER_FIELDS || f === "has";

  // "Big  Breasts" / full-width letters / capitals all compare equal
  const norm = (s) => String(s == null ? "" : s).normalize("NFKC").toLowerCase();

  // ---------- reading a query ----------
  // -> [{raw, neg, field, value, quoted}]   (raw = the exact text of the term, used to edit the query)
  function tokenize(text) {
    const out = [];
    const re = /(-?)(?:([A-Za-z]+):)?(?:"([^"]*)(")?|(\S*))/y;
    let i = 0;
    while (i < text.length) {
      if (/\s/.test(text[i])) { i++; continue; }
      re.lastIndex = i;
      const m = re.exec(text);
      if (!m || m[0] === "") { i++; continue; }
      const field = m[2] ? m[2].toLowerCase() : null;
      const body = m[3] !== undefined ? m[3] : m[5];
      const term = { raw: m[0], neg: m[1] === "-", field, value: body, quoted: m[3] !== undefined && m[4] !== undefined };
      if (field && !isField(field)) {             // "re:zero": not a prefix we know, so it is just a word
        term.field = null; term.value = m[2] + ":" + body; term.quoted = false;
      }
      i = re.lastIndex;
      out.push(term);
    }
    return out;
  }

  // "30" -> 30, "1k" -> 1000, "2.5m" -> 2500000, anything else -> null
  function amount(s) {
    const m = /^(\d+(?:\.\d+)?)([km]?)$/i.exec(s.trim());
    return m ? parseFloat(m[1]) * ({ k: 1e3, m: 1e6 }[m[2].toLowerCase()] || 1) : null;
  }
  // ">30", ">=1k", "<5", "=48", "48", "20-40" -> function(number) -> true/false, or null while it is not complete
  function range(text) {
    text = text.trim();
    let m = /^(>=|<=|>|<|=)?\s*(.+)$/.exec(text);
    if (m && amount(m[2]) !== null) {
      const n = amount(m[2]);
      return { ">": (x) => x > n, ">=": (x) => x >= n, "<": (x) => x < n, "<=": (x) => x <= n }[m[1]] || ((x) => x === n);
    }
    m = /^(.+?)\s*-\s*(.+)$/.exec(text);
    if (m && amount(m[1]) !== null && amount(m[2]) !== null) {
      const lo = Math.min(amount(m[1]), amount(m[2])), hi = Math.max(amount(m[1]), amount(m[2]));
      return (x) => x >= lo && x <= hi;
    }
    return null;
  }

  // One term -> {neg, test(doc)}, or null when it is empty or still being typed.
  function compile(tok) {
    const v = norm(tok.value).trim();
    if (!v || v === "-") return null;
    const { field } = tok;
    let test;
    if (!field) {
      test = (d) => d.text.includes(v);
    } else if (field in TAG_FIELDS) {
      const kind = TAG_FIELDS[field];
      test = (d) => d.tags.some((t) => (kind === "tag" || t.type === kind) && (tok.quoted ? t.key === v : t.key.includes(v)));
    } else if (field in TEXT_FIELDS) {
      const key = TEXT_FIELDS[field];
      test = key === "title" ? (d) => d.titles.some((t) => t.includes(v)) : (d) => d[key].includes(v);
    } else if (field in NUMBER_FIELDS) {
      const key = NUMBER_FIELDS[field], fn = range(v);
      if (!fn) return null;
      test = (d) => d[key] !== null && fn(d[key]);
    } else {                                       // has:
      if (v === "meta") test = (d) => d.hasMeta;
      else if (v === "tags") test = (d) => d.tags.length > 0;
      else return null;
    }
    return { neg: tok.neg, test };
  }

  function parse(text) {
    const tokens = tokenize(text || "");
    return { tokens, terms: tokens.map(compile).filter(Boolean) };
  }
  const matches = (query, doc) => query.terms.every((t) => t.test(doc) !== t.neg);

  // ---------- what is searched for each manga ----------
  // meta may be the short form from a list ("type:name" strings) or the full form (objects); either may be null.
  function tagsOf(meta) {
    return ((meta && meta.tags) || []).map((t) => {
      if (typeof t === "string") { const i = t.indexOf(":"); return i < 0 ? { type: "tag", label: t } : { type: t.slice(0, i), label: t.slice(i + 1) }; }
      return { type: t.type || "tag", label: t.name };
    }).map((t) => ({ ...t, key: norm(t.label) }));
  }

  function doc({ name, author, pages, meta }) {
    const m = meta || {};
    const tags = tagsOf(meta);
    const titles = [name, m.title, m.english, m.japanese, m.pretty].filter(Boolean).map(norm);
    const year = m.uploaded ? new Date(m.uploaded * 1000).getFullYear() : null;
    return {
      hasMeta: !!meta,
      tags, titles,
      author: norm(author), scanlator: norm(m.scanlator),
      pages: typeof pages === "number" ? pages : null,
      favorites: typeof m.favorites === "number" ? m.favorites : null,
      year, id: typeof m.id === "number" ? m.id : null,
      text: [...titles, norm(author), norm(m.scanlator), m.id ? String(m.id) : "", ...tags.map((t) => t.key)].filter(Boolean).join("\n"),
    };
  }

  // Shown under "?" on the library pages (see MM.shortcuts: "#" starts a heading)
  const searchHelp = [
    ["#", "Search words"],
    ["tag:glasses", "Has a tag like this (any kind of tag)"],
    ['tag:"glasses"', "Quotes: exactly this tag"],
    ["-tag:ahegao", "Without it (a minus works in front of anything)"],
    ["artist: group: parody: character: language: category:", "Same, but only that kind of tag"],
    ["title: author: scanlator:", "Search just that field"],
    ["pages:>30 pages:20-40", "Number of pages"],
    ["favorites:>1k year:2021 id:374818", "Likes, year uploaded, gallery id"],
    ["has:meta -has:meta", "Only manga with / without information"],
  ];

  // ---------- editing a query from the tag panel ----------
  // The search box stays the only place the filter lives: clicking a tag just adds or removes a term in it.
  const tagToken = (type, label, neg) =>
    (neg ? "-" : "") + (type in TAG_FIELDS ? type : "tag") + ':"' + String(label).replace(/"/g, "") + '"';

  const isTagTerm = (tok, type, label) =>
    tok.field in TAG_FIELDS && (TAG_FIELDS[tok.field] === "tag" || TAG_FIELDS[tok.field] === type) && norm(tok.value).trim() === norm(label);

  // "in" (must have it) / "out" (must not) / null, for one tag in the current query
  function tagState(text, type, label) {
    const tok = tokenize(text).find((t) => isTagTerm(t, type, label));
    return tok ? (tok.neg ? "out" : "in") : null;
  }
  // The query with that tag set to "in", "out" or null (removed)
  function setTag(text, type, label, state) {
    const keep = tokenize(text).filter((t) => !isTagTerm(t, type, label)).map((t) => t.raw);
    if (state) keep.push(tagToken(type, label, state === "out"));
    return keep.join(" ");
  }
  const tagTermCount = (text) => tokenize(text).filter((t) => t.field in TAG_FIELDS && norm(t.value).trim()).length;
  // The query without any tag term
  const clearTags = (text) => tokenize(text).filter((t) => !(t.field in TAG_FIELDS)).map((t) => t.raw).join(" ");
  // tagState for many tags at once: reads the query once, returns (type, label) -> "in" | "out" | null
  function tagStates(text) {
    const terms = tokenize(text).filter((t) => t.field in TAG_FIELDS);
    return (type, label) => {
      const hit = terms.find((t) => isTagTerm(t, type, label));
      return hit ? (hit.neg ? "out" : "in") : null;
    };
  }

  // ---------- display ----------
  const title = (meta, fallback) => (meta && meta.title) || fallback;

  const number = (n) => n.toLocaleString();
  // 13509 -> "13.5K" (for the small line under a card)
  const compact = (n) => new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(n);
  function date(seconds) {
    const d = new Date(seconds * 1000);
    return isNaN(d) ? "" : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  // [{before, value, after}] for the small fact chips of a manga page (pages and chapters are added by the page itself)
  function facts(meta) {
    const out = [];
    if (!meta) return out;
    if (meta.id) out.push({ before: "ID ", value: String(meta.id) });
    if (meta.favorites !== undefined) out.push({ value: number(meta.favorites), after: " favorites" });
    if (meta.uploaded) { const d = date(meta.uploaded); if (d) out.push({ before: "Uploaded ", value: d }); }
    if (meta.scanlator) out.push({ before: "Scanlator ", value: meta.scanlator });
    return out;
  }
  function factItem(fact) {
    const li = document.createElement("li");
    const b = document.createElement("b");
    b.textContent = fact.value;
    li.append(fact.before || "", b, fact.after || "");
    return li;
  }

  // Tags grouped by kind -> [{type, label, names}]
  function groupTags(meta) {
    const groups = new Map();
    for (const t of (meta && meta.tags) || []) {
      const type = t.type || "tag";
      if (!groups.has(type)) groups.set(type, []);
      groups.get(type).push(t.name);
    }
    const rank = (type) => (TYPE_ORDER.includes(type) ? TYPE_ORDER.indexOf(type) : TYPE_ORDER.length);
    return [...groups.entries()]
      .sort((a, b) => rank(a[0]) - rank(b[0]) || a[0].localeCompare(b[0]))
      .map(([type, names]) => ({
        type, names: names.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" })),
        label: TYPE_LABEL[type] || type.charAt(0).toUpperCase() + type.slice(1),
      }));
  }

  // The link a tag points to: the library, filtered by that tag
  const tagHref = (type, label) => "/?q=" + enc(tagToken(type, label));

  // The tag lists of one manga: a row per kind, each tag a link to the library filtered by it.
  // Returns null when there are no tags. newTab: open the library in a new tab (used inside the reader, which should keep its place).
  function renderTags(meta, { newTab = false } = {}) {
    const groups = groupTags(meta);
    if (!groups.length) return null;
    const root = document.createElement("div");
    root.className = "tagrows";
    for (const group of groups) {
      const row = document.createElement("div");
      row.className = "tagrow";
      const label = document.createElement("span");
      label.className = "tagrow-label"; label.textContent = group.label;
      const list = document.createElement("div");
      list.className = "taglist";
      for (const name of group.names) {
        const a = document.createElement("a");
        a.className = "tag t-" + group.type.replace(/[^a-z0-9]/g, "");
        a.href = tagHref(group.type, name);
        a.textContent = name;
        a.title = "Show every manga with this tag";
        if (newTab) { a.target = "_blank"; a.rel = "noopener"; }
        list.appendChild(a);
      }
      row.append(label, list);
      root.appendChild(row);
    }
    return root;
  }

  MM.meta = {
    TYPE_ORDER, TYPE_LABEL, TAG_FIELDS,
    norm, tokenize, parse, matches, doc, range, tagsOf,
    tagToken, tagState, tagStates, setTag, tagTermCount, clearTags, searchHelp,
    title, number, compact, facts, factItem, groupTags, tagHref, renderTags,
  };
})();
