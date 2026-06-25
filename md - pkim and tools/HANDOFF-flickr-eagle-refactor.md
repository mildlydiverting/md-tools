# Handoff: Flickr/Eagle tooling refactor
_Updated June 2026_

---

## What problem started this

Dropbox was failing to sync Eagle library images because filenames contained special characters — accented letters (`é`, `à`), curly quotes, colons etc. — coming from Flickr photo titles. The chain was:

1. `flickr_download.py` saves title into filename via `safe_filename()` — but `isalnum()` passes Unicode letters through
2. `eagle_import.py` passes the raw title to Eagle as the item `name`
3. Eagle uses that name as the image filename inside the `.info` folder
4. Dropbox refuses to sync it

---

## Decisions made

### Filenames: use photo_id only
Instead of `{photo_id}_{title}.jpg`, files are now just `{photo_id}.jpg`. The title lives inside the sidecar JSON, the Eagle annotation block, and citations — not in the filename. Photo IDs are pure digits, always short, always safe.

### Eagle item name: use photo_id
`eagle_import.py` passes `photo_id` as the Eagle `name` field, not the title. Title is in the annotation YAML.

---

## Files in this folder

### `fix_filenames.py` — three modes

```bash
# 1. Rename Eagle .info image files to Flickr photo_id
#    (extracts ID from source_url in annotation; falls back to safe ASCII title)
python fix_filenames.py eagle  /path/to/Eagle.library/images --dry-run
python fix_filenames.py eagle  /path/to/Eagle.library/images

# 2. Fix name/file mismatches + corrupted JSON in Eagle .info folders
python fix_filenames.py eagle-repair /path/to/Eagle.library/images --dry-run
python fix_filenames.py eagle-repair /path/to/Eagle.library/images --fix-bad-json

# 3. Rename Flickr downloads to photo_id-only filenames
python fix_filenames.py flickr /path/to/flickr_downloads --dry-run
python fix_filenames.py flickr /path/to/flickr_downloads
```

**Always dry-run first. Quit Eagle fully before running any eagle mode.**

### `flickr_download_safe_filename_patch.py`
Instructions for patching `flickr_download.py` — the uploaded version already has these changes applied.

### `eagle_import_patch.py`
Two changes for `eagle_import.py`:
- `name = meta.get("photo_id") or image_path.stem`
- Replace `build_annotation()` with the version in this file (fixes YAML line-wrapping, adds title field, removes HTML tags from URLs)

---

## Current state of the Eagle library repair

### What works
- `fix_filenames.py eagle` mode: renames image files inside `.info` folders from long titles to photo_id. **Confirmed working** — 14,000+ items processed.
- `fix_filenames.py eagle-repair --fix-bad-json`: fixes 12 corrupted metadata.json files (two JSON objects concatenated — Eagle race condition). **Confirmed working.**
- `eagle-repair` detects and patches name/file mismatches.

### What is NOT working — the core unresolved problem

**Eagle overwrites our metadata.json edits.**

Eagle watches `.info` folders and pushes its in-memory state back to disk. Even when Eagle is fully quit, on reopen it reverts metadata.json `name` to its cached value. Evidence:
- `$$hashKey` fields appear in palettes (Eagle's internal Angular.js tracking)
- `lastModified` updates to a newer value than our repair wrote
- The `name` field reverts to the old value

Attempted fixes that didn't work:
- Updating `lastModified` to current time (Eagle still wins)
- Clearing `noThumbnail: true` flag
- Running with Eagle fully closed

### Why only 4 mismatches detected
The `eagle-repair` script finds mismatches where `{name}.{ext}` file doesn't exist but another jpg does. Many broken items may have Eagle reverting metadata.json so the name matches the OLD filename again — making them look "correct" to the script, even though the image is still broken in Eagle's display.

### Root cause hypothesis
Eagle has an internal database (likely IndexedDB via Electron, or a library-level JSON) separate from individual `metadata.json` files. This internal DB holds the canonical item state and overwrites metadata.json on startup/sync. We need to update Eagle's internal DB, not just the files.

### Possible next approaches

**Option A: Use Eagle's API**
Eagle runs a local API on port 41595. The `item/update` endpoint should update both the internal DB and metadata.json atomically. This requires Eagle to be OPEN.

```python
import requests
requests.post("http://localhost:41595/api/item/update", json={
    "id": "MQIQ51NC6EF4Q",
    "name": "47092264742"
})
```

This is probably the correct solution. Write an `eagle_repair_via_api.py` script that:
1. Scans .info folders for mismatches (name ≠ actual image filename stem)
2. For each mismatch, calls Eagle API to update the name
3. Eagle then handles the internal DB + metadata.json update itself

**Option B: Find and edit Eagle's internal database**
Locate the library-level database file (probably inside `Eagle.library/` at the top level, not inside `images/`). Check what's there:
```bash
ls /Users/kimplowright/Dropbox/_visualreference/inspo-and-reference.library/
```
There may be a `library.json` or similar that Eagle reads on startup.

**Option C: Re-import via eagle_import.py**
For broken items, delete and re-import via Eagle API. Nuclear option but guaranteed to work.

---

## Downstream: bigger refactor (not started)

```
md-flickr-tools/
  flickr/
    __init__.py
    auth.py          # OAuth, dotenv
    api.py           # all flickrapi calls
    meta.py          # license map, date granularity, EXIF tag map, medium hints
    tags.py          # split_tags(), parse machine/RDF tags (BHL bookid: etc.)
  meta_formats/
    __init__.py
    harvard.py       # citation_markdown string
    tasl.py          # TASL attribution line
    annotation.py    # Eagle YAML annotation block (use width=float('inf') in yaml.dump)
    frontmatter.py   # Obsidian YAML frontmatter
  schema/
    fields.md        # canonical crosswalk — read Obsidian notes first (see below)
    mapping.py       # field translation dicts
  eagle_import.py    # thin wrapper
  fix_filenames.py   # this file
  flickr_favourites_download.py
  flickr_gallery_download.py
```

**Read these Obsidian notes before designing schema/fields.md:**
- `_development-notes/md-pkim-library/Images and Collection Data - standards schema and formats.md`
- `md-pkim-library/README-extract-book-metadata.md`
- `_development-notes/md-pkim-library/museum-image-citation-structured-data-audit-handoff.md`
- `dt-knowledge-base/knowledge-base/artists/lod-lookup.yaml`

Internal schema should align to Dublin Core as hub (crosswalks to schema.org, Wikidata, MARC, VRA Core, MET API, Europeana etc.)

**BHL machine tags** (`bookid:`, `bookauthor:`, `bookleafnumber:` etc.) are rich bibliographic data parseable via Internet Archive API + Wikidata. Relevant to dt-knowledge-base. Capture for later — `flickr/tags.py` is where this belongs.

---

## Scripts committed to repo
- `fix_filenames.py` ✓
- `flickr_download.py` (updated, photo_id filenames) ✓
- `flickr_gallery_download.py` (updated, photo_id filenames) ✓
- `eagle_import_patch.py` (apply manually to eagle_import.py)
- `flickr_download_safe_filename_patch.py` (apply manually, then delete)
