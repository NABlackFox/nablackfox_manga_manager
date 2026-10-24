from utils import PAGE_RE, parse_page

def with_marker(file, chapter):
  """File path with the chapter marker set (or removed when chapter is None)."""
  digits = PAGE_RE.match(file.stem).group(1)
  marker = f"-chapter{chapter}" if chapter else ""
  return file.with_name(f"{digits}{marker}{file.suffix}")

def check_start(chapter, start, pages, markers):
  """Raise ValueError if `start` is not a valid first page for the chapter."""
  if start not in pages:
    raise ValueError(f"Page {start} does not exist in this folder.")
  if len(pages[start]) > 1:
    raise ValueError(f"Page {start} exists more than once (different extensions).")
  for other, entries in markers.items():
    if other == chapter:
      continue
    for number, _file in entries:
      if other < chapter and number >= start:
        raise ValueError(
            f"Chapter {other} starts at page {number}, "
            f"so chapter {chapter} must start after it."
        )
      if other > chapter and number <= start:
        raise ValueError(
            f"Chapter {other} starts at page {number}, "
            f"so chapter {chapter} must start before it."
        )

def plan_marker(chapter, start, pages, markers):
  """List the renames needed to make `start` the first page of the chapter."""
  check_start(chapter, start, pages, markers)
  renames = []
  # Remove the old marker (if any) first.
  for number, file in markers.get(chapter, []):
    if number != start:
      renames.append((file, with_marker(file, None)))
  # Then mark the new first page, keeping its extension.
  target = pages[start][0]
  if parse_page(target)[1] != chapter:
    renames.append((target, with_marker(target, chapter)))
  return renames

def apply_renames(renames):
  """Do the renames; if one fails, undo the ones already done."""
  done = []
  try:
    for source, target in renames:
      if target.exists():
        raise FileExistsError(f"{target.name} already exists")
      source.rename(target)
      done.append((source, target))
  except BaseException:
    for source, target in reversed(done):
      try:
        target.rename(source)
      except OSError:
        pass
    raise