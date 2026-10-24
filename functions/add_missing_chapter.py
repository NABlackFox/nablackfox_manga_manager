import helpers.chapter_ranges as chapter_ranges
import helpers.splice as splice

def parse_position(text, count, pages, markers):
  """Turn the typed chapter number into (chapter, page where it starts).

  Chapter count + 1 means "after the last chapter".
  """
  if not text.isdigit() or not 1 <= int(text) <= count + 1:
    raise ValueError(f"Enter a chapter from 1 to {count + 1}.")
  chapter = int(text)
  return chapter, chapter_ranges.insert_position(chapter, count, pages, markers)

def build_add_missing_plan(info, first_chapter, start, file_plan, folder_count):
  """Plan for putting folder_count chapter folders in at `start`.

  The chapters that follow move up by folder_count (markers and pages).
  """
  new_pages = chapter_ranges.mark_new_pages(file_plan, first_chapter)
  return splice.build_splice_plan(info, start, start - 1, new_pages, folder_count)