// Shared by the downloader modules: small helpers and the list of picked galleries.
const Admin = (() => {
  const $ = (id) => document.getElementById(id);

  async function api(path, options) {
    const res = await fetch(path, options);
    let body = null;
    try { body = await res.json(); } catch (_) {}
    if (!res.ok) throw new Error((body && body.error) || "Request failed (" + res.status + ")");
    return body;
  }
  const post = (path, data) => api(path, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data || {}),
  });

  const store = {
    get(key, fallback) { try { const v = localStorage.getItem("admin-" + key); return v === null ? fallback : v; } catch (_) { return fallback; } },
    set(key, value) { try { localStorage.setItem("admin-" + key, value); } catch (_) {} },
  };

  // Galleries ticked in the results: id -> title. search.js changes it, downloads.js reads it.
  const picked = new Map();
  const listeners = [];
  const onPickedChange = (fn) => listeners.push(fn);
  const pickedChanged = () => listeners.forEach((fn) => fn());

  return { $, api, post, store, picked, onPickedChange, pickedChanged };
})();
