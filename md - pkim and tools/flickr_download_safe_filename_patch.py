"""
PATCH for flickr_download.py
------------------------------
Simplification: filenames use bare photo_id only. The title lives in the
sidecar JSON and Eagle annotation — not in the filename.

── 1. Remove safe_filename() entirely (lines ~335-336) ──────────────────────

Delete:
    def safe_filename(s, max_len=60):
        return "".join(c if c.isalnum() or c in ' _-' else '_' for c in s)[:max_len].strip()

── 2. Change the base filename in process_photo() (lines ~341-343) ──────────

OLD:
    base  = f"{photo_id}_{safe_filename(title)}"
    img_path  = os.path.join(output_dir, f"{base}.jpg")
    json_path = os.path.join(output_dir, f"{base}.json")

NEW:
    img_path  = os.path.join(output_dir, f"{photo_id}.jpg")
    json_path = os.path.join(output_dir, f"{photo_id}.json")

── 3. Update the manifest entry (lines ~513-515) ────────────────────────────

OLD:
    manifest[photo_id] = {
        'date_accessed': date_accessed,
        'filename':      f"{base}.jpg",
        'size_label':    size_label,
    }

NEW:
    manifest[photo_id] = {
        'date_accessed': date_accessed,
        'filename':      f"{photo_id}.jpg",
        'size_label':    size_label,
    }

── 4. eagle_import.py: name field ───────────────────────────────────────────

In import_folder(), change:

    name = meta.get("title") or image_path.stem

to:

    name = meta.get("photo_id") or image_path.stem

Eagle will show the photo_id as the item name. The full title is in the
annotation YAML block (citation_markdown, tasl, title fields).
"""
