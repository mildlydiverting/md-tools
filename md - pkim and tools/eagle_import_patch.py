"""
PATCH for eagle_import.py
--------------------------
Use photo_id as the Eagle item name instead of the title.
The title remains in the annotation YAML (citation_markdown, tasl, title fields).

ONE change needed — in import_folder(), around line 280:

OLD:
    name = meta.get("title") or image_path.stem

NEW:
    name = meta.get("photo_id") or image_path.stem

That's it. Eagle will show the photo_id as the item name. The full title,
TASL, and citation are in the annotation block where they were already.

No safe_filename() function needed — photo_ids are pure digits, always safe.
"""
