from utils import list_images, parse_page, page_name
from helpers.splice import recycle

STAGING_NAME = ".delete_pages_staging"


def delete_and_renumber(folder, selected_numbers):
  """Delete selected page numbers, renumber the rest, and keep chapter markers.

  Selected images are moved to a staging folder first. If renumbering fails,
  the original filenames are restored. After a successful renumber, the staging
  folder is sent to the recycle bin using the project's existing helper.
  """
  selected_numbers = set(selected_numbers)
  numbered = []

  for file in list_images(folder):
    parsed = parse_page(file)
    if parsed:
      numbered.append((parsed[0], file, parsed[1]))

  if not numbered:
    raise ValueError("No numbered page images were found in this folder.")

  numbered.sort(key=lambda item: (item[0], item[1].name.casefold()))

  pages = {}
  for number, file, _chapter in numbered:
    pages.setdefault(number, []).append(file)

  duplicates = [
      number for number, files in pages.items()
      if len(files) > 1
  ]
  if duplicates:
    raise ValueError(
        "Page number(s) appear more than once with different extensions: "
        + ", ".join(map(str, duplicates))
        + ". Fix these duplicates before deleting pages."
    )

  known_numbers = set(pages)
  missing = selected_numbers - known_numbers
  if missing:
    raise ValueError(
        "Selected page(s) no longer exist: "
        + ", ".join(map(str, sorted(missing)))
    )
  if not selected_numbers:
    raise ValueError("Select at least one page.")

  staging = folder / STAGING_NAME
  if staging.exists():
    raise FileExistsError(
        f"{staging.name} already exists. Check it before running this again."
    )

  # Record which chapter each page belongs to, based on existing markers.
  current_chapter = None
  survivors = []
  selected_files = []
  first_survivor_by_chapter = {}

  for number, file, chapter in numbered:
    if chapter is not None:
      current_chapter = chapter

    if number in selected_numbers:
      selected_files.append(file)
    else:
      survivors.append((number, file, current_chapter))
      if current_chapter is not None:
        first_survivor_by_chapter.setdefault(current_chapter, file)

  # Move each marker to the first remaining page in its chapter.
  # If a whole chapter was deleted, its marker is removed.
  marker_for_file = {
      file: chapter
      for chapter, file in first_survivor_by_chapter.items()
  }

  width = max(
      3,
      max(len(str(number)) for number, _file, _chapter in numbered)
  )

  targets = []
  for new_number, (_old_number, file, _chapter) in enumerate(
      survivors, start=1
  ):
    chapter = marker_for_file.get(file)
    target = file.with_name(
        page_name(new_number, width, file.suffix, chapter)
    )
    targets.append((file, target))

  # Keep a move log so filename changes can be rolled back if a step fails.
  moved = []

  def move(source, target):
    source.rename(target)
    moved.append((source, target))

  try:
    staging.mkdir()

    # Move deleted pages out of the way.
    for file in selected_files:
      move(file, staging / file.name)

    # Stage all surviving pages to avoid filename collisions.
    staged_survivors = []
    for index, (file, target) in enumerate(targets):
      temp = folder / f".__delete_pages_tmp_{index}{file.suffix}"
      if temp.exists():
        raise FileExistsError(f"Temporary file already exists: {temp.name}")
      move(file, temp)
      staged_survivors.append((temp, target))

    # Rename the staged pages to their final page numbers.
    for temp, target in staged_survivors:
      if target.exists():
        raise FileExistsError(f"{target.name} already exists")
      move(temp, target)

  except BaseException:
    # Undo completed moves in reverse order.
    for source, target in reversed(moved):
      try:
        if target.exists():
          target.rename(source)
      except OSError:
        pass

    # Only remove the staging directory if it is empty.
    # Never delete files that could not be restored.
    try:
      staging.rmdir()
    except OSError:
      pass

    raise

  # Match the rest of the app: send removed content to the recycle bin.
  recycle_error = recycle(staging)

  return len(selected_files), len(survivors), recycle_error