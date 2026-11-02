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

  return { $, enc, params, store, mangaQuery, groupKey, getJson };
})();
