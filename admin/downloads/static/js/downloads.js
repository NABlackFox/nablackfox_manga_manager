// Downloads module: the Download button and the queue panel.
(() => {
  const { $, api, post, picked, onPickedChange } = Admin;
  let timer = null;

  const label = { queued: "Waiting", downloading: "Downloading", done: "Saved", failed: "Failed", skipped: "Skipped", cancelled: "Cancelled" };
  const mb = (n) => (n / 1048576).toFixed(1) + " MB";

  function render(data) {
    const jobs = data.jobs.slice().reverse();      // newest first
    $("queue-empty").hidden = jobs.length > 0;
    $("queue-tools").hidden = jobs.length === 0;
    $("jobs").replaceChildren(...jobs.map((job) => {
      const li = document.createElement("li");
      li.className = "job " + job.status;
      const title = document.createElement("span");
      title.className = "t"; title.textContent = job.title; title.title = job.file || job.title;
      const status = document.createElement("div");
      status.className = "s";
      const left = document.createElement("b");
      left.textContent = label[job.status] || job.status;
      const right = document.createElement("span");
      if (job.status === "downloading") right.textContent = job.total ? mb(job.downloaded) + " / " + mb(job.total) : mb(job.downloaded);
      else if (job.error) right.textContent = job.error;
      else if (job.status === "done") right.textContent = "in the zip folder";
      status.append(left, right);
      li.append(title, status);
      if (job.status === "downloading") {
        const bar = document.createElement("div"); bar.className = "bar" + (job.total ? "" : " indeterminate");
        const fill = document.createElement("i"); if (job.total) fill.style.width = Math.min(100, job.downloaded / job.total * 100) + "%";
        bar.appendChild(fill); li.appendChild(bar);
      }
      if (job.status === "failed" || job.status === "cancelled") {
        const retry = document.createElement("button");
        retry.textContent = "Try again";
        retry.onclick = async () => { await post("/api/downloads/retry", { id: job.id }); poll(); };
        li.appendChild(retry);
      }
      return li;
    }));
  }

  async function poll() {
    clearTimeout(timer);
    try {
      const data = await api("/api/downloads");
      render(data);
      if (data.active) timer = setTimeout(poll, 1500);   // keep watching only while something is running
    } catch (_) { timer = setTimeout(poll, 5000); }
  }

  function updateBar() {
    $("pickbar").hidden = picked.size === 0;
    $("pick-count").textContent = picked.size + " selected";
  }
  onPickedChange(updateBar);

  $("download").addEventListener("click", async () => {
    const ids = [...picked.keys()];
    if (!ids.length) return;
    $("download").disabled = true; $("download").classList.add("loading");
    try {
      await post("/api/downloads", { ids });
      picked.clear();
      document.querySelectorAll(".card.selected").forEach((c) => c.classList.remove("selected"));
      updateBar();
      poll();
    } catch (error) { alert(error.message); }
    $("download").disabled = false; $("download").classList.remove("loading");
  });
  $("cancel-queued").addEventListener("click", async () => { await post("/api/downloads/cancel"); poll(); });
  $("clear-finished").addEventListener("click", async () => { await post("/api/downloads/clear"); poll(); });

  poll();
})();
