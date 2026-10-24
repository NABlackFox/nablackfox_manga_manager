import helpers.chapter_ranges as chapter_ranges
import helpers.splice as splice

def parse_chapter(text, count, pages, markers):
  """Turn the typed chapter number into (chapter, (first page, last page))."""
  if not text.isdigit() or not 1 <= int(text) <= count:
    raise ValueError(f"Enter a chapter from 1 to {count}.")
  chapter = int(text)
  return chapter, chapter_ranges.chapter_pages(chapter, count, pages, markers)

def build_update_plan(info, chapter, start, end, new_files):
  """Plan for replacing pages start-end with new_files (any length).

  The pages after the chapter shift by the difference; chapter numbers stay.
  """
  new_pages = [(file, chapter if i == 0 else None) for i, file in enumerate(new_files)]
  return splice.build_splice_plan(info, start, end, new_pages, 0)