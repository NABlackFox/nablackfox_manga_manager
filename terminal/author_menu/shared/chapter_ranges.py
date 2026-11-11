# Where chapters start and end, worked out from the markers in a merged folder.

def chapter_start(chapter, markers):
  """First page of a chapter, read from its marker."""
  entries = markers.get(chapter)
  if not entries:
    raise ValueError(
        f"Chapter {chapter} has no marker. Set it first with 'Edit chapter marker'."
    )
  if len(entries) > 1:
    raise ValueError(f"Chapter {chapter} has more than one marker.")
  return entries[0][0]

def chapter_pages(chapter, count, pages, markers):
  """(first page, last page) of a chapter."""
  start = chapter_start(chapter, markers)
  if chapter < count:
    end = chapter_start(chapter + 1, markers) - 1
  else:
    end = max(pages)
  if end < start:
    raise ValueError(f"The markers of chapter {chapter} and the next one are out of order.")
  return start, end

def insert_position(chapter, count, pages, markers):
  """Page where a new chapter numbered `chapter` has to start."""
  if chapter > count:
    return max(pages) + 1
  return chapter_start(chapter, markers)

def mark_new_pages(plan, first_chapter):
  """[(file, label)] -> [(file, chapter number or None)].

  The first page of every folder (label change) gets the chapter number.
  """
  result = []
  chapter = first_chapter - 1
  last_label = None
  for file, label in plan:
    marker = None
    if label != last_label:
      chapter += 1
      marker = chapter
      last_label = label
    result.append((file, marker))
  return result