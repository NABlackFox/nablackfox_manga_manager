import helpers.chapter_ranges as chapter_ranges
import helpers.merged_folder as merged_folder
import helpers.splice as splice

def build_add_new_plan(info, folder, file_plan):
  """Plan for adding new chapter folders after the last page.

  file_plan is the list from merge_manga.build_plan.
  Returns (plan, number of the first new chapter).
  """
  first_chapter = merged_folder.chapter_count(folder, info) + 1
  start = info.last_number + 1
  new_pages = chapter_ranges.mark_new_pages(file_plan, first_chapter)
  plan = splice.build_splice_plan(info, start, start - 1, new_pages, 0)
  return plan, first_chapter