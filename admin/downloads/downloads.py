"""Downloads queue: asks the API for each gallery's zip and saves it into the zip source folder.

Public API: DownloadQueue(client, folder, user_agent) with enqueue / snapshot / retry / clear_finished / cancel_queued.
The zips are left for the terminal to handle ("Grab zip file", then unzip, convert, merge).
"""
import re
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

from admin.shared import catalog
from admin.shared.nhentai_client import ApiError

CHUNK = 64 * 1024
MAX_DOWNLOAD = 2 * 1024 ** 3        # a manga zip is far smaller: stop a runaway download
MAX_UNZIPPED = 4 * 1024 ** 3        # refuse "zip bombs" that unzip to something huge
MAX_FILES = 5000
# nothing a manga zip needs, and all of it can run or script when opened by accident
RISKY_EXTENSIONS = {".exe", ".bat", ".cmd", ".com", ".scr", ".msi", ".ps1", ".vbs", ".vbe", ".js", ".jse", ".wsf",
                    ".lnk", ".hta", ".jar", ".dll", ".sh", ".reg", ".cpl", ".pif", ".html", ".htm", ".svg", ".url"}
FINISHED = ("done", "failed", "skipped", "cancelled")
BAD_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_name(name, limit=150):
  name = BAD_NAME_CHARS.sub("", name)
  name = re.sub(r"\s+", " ", name).strip(" .")
  return name[:limit].strip(" .")


def file_name(gallery_id, title, disposition=None):
  """Name of the saved zip. Always starts with nhentai-<id> so 'Grab zip file' and author matching recognise it."""
  name = None
  if disposition:
    match = re.search(r"filename\*\s*=\s*[\w-]+''([^;]+)", disposition) or re.search(r'filename\s*=\s*"?([^";]+)"?', disposition)
    if match:
      name = clean_name(Path(unquote(match.group(1))).name)
  if not name:
    name = clean_name(f"nhentai-{gallery_id} - {title}") if title else f"nhentai-{gallery_id}"
  if not re.match(rf"nhentai-{gallery_id}\b", name, re.IGNORECASE):
    name = clean_name(f"nhentai-{gallery_id} - {name}")
  if not name.lower().endswith(".zip"):
    name = name.rsplit(".", 1)[0] + ".zip" if name.lower().endswith(".cbz") else name + ".zip"
  return name


def inspect_zip(path):
  """Why this zip should not be kept (a short sentence), or None when it looks like a normal manga zip.

  Nothing is extracted here. It checks the list of names and sizes only.
  """
  try:
    with zipfile.ZipFile(path) as archive:
      infos = archive.infolist()
  except (zipfile.BadZipFile, OSError):
    return "it is not a valid zip file"
  if len(infos) > MAX_FILES:
    return f"it holds {len(infos)} files"
  total = 0
  for info in infos:
    parts = PurePosixPath(info.filename.replace("\\", "/")).parts
    if ".." in parts or PurePosixPath(info.filename).is_absolute() or (parts and ":" in parts[0]):
      return "it has a file path that points outside its own folder"
    if Path(info.filename).suffix.lower() in RISKY_EXTENSIONS:
      return f"it contains a {Path(info.filename).suffix.lower()} file ({Path(info.filename).name})"
    total += info.file_size
  if total > MAX_UNZIPPED:
    return f"it would unzip to {total / 1024 ** 3:.1f} GB"
  return None


class DownloadQueue:
  def __init__(self, client, folder, opener=urllib.request.urlopen):
    self.client = client
    self.folder = Path(folder)
    self._opener = opener
    self._jobs = {}            # gallery id -> job dict, in the order they were added
    self._lock = threading.Lock()
    self._wake = threading.Condition(self._lock)
    self._stopping = False
    self._worker = threading.Thread(target=self._loop, daemon=True)
    self._worker.start()

  # ----- what the page uses -----

  def enqueue(self, ids):
    """Add galleries. Ones already waiting or running are left alone; finished ones are queued again."""
    added = 0
    with self._wake:
      for gallery_id in ids:
        job = self._jobs.get(gallery_id)
        if job and job["status"] in ("queued", "downloading"):
          continue
        self._jobs.pop(gallery_id, None)
        self._jobs[gallery_id] = {
            "id": gallery_id, "title": catalog.get(gallery_id).get("title") or f"#{gallery_id}",
            "status": "queued", "downloaded": 0, "total": None, "error": None, "file": None,
        }
        added += 1
      self._wake.notify()
    return added

  def snapshot(self):
    with self._lock:
      jobs = [dict(job) for job in self._jobs.values()]
    active = sum(job["status"] in ("queued", "downloading") for job in jobs)
    return {"jobs": jobs, "active": active, "folder": str(self.folder)}

  def retry(self, gallery_id):
    with self._wake:
      job = self._jobs.get(gallery_id)
      if job and job["status"] in ("failed", "cancelled"):
        job.update(status="queued", error=None, downloaded=0, total=None)
        self._wake.notify()

  def cancel_queued(self):
    with self._lock:
      for job in self._jobs.values():
        if job["status"] == "queued":
          job["status"] = "cancelled"

  def clear_finished(self):
    with self._lock:
      for gallery_id in [i for i, job in self._jobs.items() if job["status"] in FINISHED]:
        del self._jobs[gallery_id]

  def shutdown(self):
    with self._wake:
      self._stopping = True
      self._wake.notify_all()

  # ----- the worker -----

  def _next_job(self):
    with self._wake:
      while not self._stopping:
        for job in self._jobs.values():
          if job["status"] == "queued":
            job["status"] = "downloading"
            return job
        self._wake.wait()
    return None

  def _loop(self):
    while True:
      job = self._next_job()
      if job is None:
        return
      try:
        self._download(job)
      except ApiError as error:
        self._finish(job, "failed", str(error))
      except Exception as error:   # keep the queue alive whatever happens to one gallery
        self._finish(job, "failed", f"Unexpected problem: {error}")

  def _finish(self, job, status, error=None):
    with self._lock:
      job["status"] = status
      job["error"] = error

  def _existing(self, gallery_id):
    try:
      for file in self.folder.iterdir():
        if file.is_file() and file.suffix.lower() == ".zip" and re.match(rf"nhentai-{gallery_id}\b", file.name, re.IGNORECASE):
          return file
    except OSError:
      pass
    return None

  def _download(self, job):
    gallery_id = job["id"]
    self.folder.mkdir(parents=True, exist_ok=True)
    existing = self._existing(gallery_id)
    if existing:
      job["file"] = existing.name
      return self._finish(job, "skipped", "Already in the zip folder.")

    info = self.client.request("POST", f"/galleries/{gallery_id}/download", {"format": "zip"}, group="download")
    url = info.get("url") if isinstance(info, dict) else None
    if not url or urlparse(url).scheme not in ("http", "https"):
      raise ApiError("The site did not give a download address. Does your API key allow downloads?")

    request = urllib.request.Request(url, headers={"User-Agent": self.client.user_agent})   # no API key here
    try:
      response = self._opener(request, timeout=60)
    except urllib.error.HTTPError as error:
      raise ApiError(f"The zip download failed ({error.code}).", error.code) from None
    except (urllib.error.URLError, OSError) as error:
      raise ApiError(f"The zip download failed ({getattr(error, 'reason', error)}).") from None

    with response:
      name = file_name(gallery_id, catalog.get(gallery_id).get("title"), response.headers.get("Content-Disposition"))
      target = self.folder / name
      part = self.folder / f".{name}.part"
      total = response.headers.get("Content-Length")
      with self._lock:
        job["file"], job["total"] = name, int(total) if total and total.isdigit() else None
      try:
        with open(part, "wb") as out:
          while not self._stopping:
            chunk = response.read(CHUNK)
            if not chunk:
              break
            out.write(chunk)
            with self._lock:
              job["downloaded"] += len(chunk)
            if job["downloaded"] > MAX_DOWNLOAD:
              raise ApiError("The download is far bigger than a manga should be, so it was stopped.")
        if self._stopping:
          raise ApiError("Stopped.")
        if not zipfile.is_zipfile(part):
          raise ApiError("What came back is not a zip file (the link may have expired).")
        reason = inspect_zip(part)
        if reason:
          raise ApiError(f"Deleted for safety: {reason}.")
        if target.exists():
          return self._finish(job, "skipped", "Already in the zip folder.")
        part.replace(target)
      finally:
        part.unlink(missing_ok=True)
    self._finish(job, "done")
