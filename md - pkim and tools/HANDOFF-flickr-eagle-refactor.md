# Handoff: Flickr/Eagle tooling refactor
_June 2026_

## What problem started this

Dropbox was failing to sync Eagle library images because filenames contained special characters — accented letters (`é`, `à`), curly quotes, colons etc. — coming from Flickr photo titles. The chain was:

1. `flickr_download.py` saves title into filename via `safe_filename()` — but `isalnum()` passes Unicode letters through
2. `eagle_import.py` passes the raw title to Eagle as the item `name`
3. Eagle uses that name as the image filename inside the `.info` folder
4. Dropbox refuses to sync it

The specific broken item that surfaced this: `/Dropbox/_visualreference/inspo-and-reference.library/images/MQIQ51GSL7YVD.info`

---

## Decisions made

### Filenames: use photo_id only
Instead of `{photo_id}_{title}.jpg`, files are now just `{photo_id}.jpg`. The title lives inside the sidecar JSON, the Eagle annotation block, and citations — not in the filename. Photo IDs are pure digits, always short, always safe.

### Eagle item name: use photo_id
`eagle_import.py` passes `photo_id` as the Eagle `name` field, not the title. Title is in the annotation YAML.

---

## Files created (all in md - pkim and tools/)

### `fix_filenames.py`
Fixes existing files on disk. Two modes:

```bash
# Rename Flickr downloads from photo_id_title.jpg → photo_id.jpg
# (reads photo_id from inside the sidecar JSON, so works even on mangled filenames)
python fix_filenames.py flickr /path/to/flickr_downloads --dry-run
python fix_filenames.py flickr /path/to/flickr_downloads

# Fix Eagle .info folders with special chars in image filenames + metadata.json
python fix_filenames.py eagle /path/to/Eagle.library/images --dry-run
python fix_filenames.py eagle /path/to/Eagle.library/images
```

Always dry-run first.

### `flickr_download_safe_filename_patch.py`
Instructions for patching `flickr_download.py` — remove `safe_filename()`, change filename lines to use `{photo_id}` directly. The uploaded `flickr_download.py` already has these changes applied.

### `eagle_import_patch.py`
One-line change to `eagle_import.py`: `name = meta.get("photo_id") or image_path.stem`

---

## Current state of the scripts

### `flickr_download.py` (uploaded, changes applied ✓)
- Downloads favourites + all galleries in one run
- Flat output folder `./flickr_downloads/`
- Deduplicates photos appearing in multiple galleries, tracks `occurrences`
- Filenames: `{photo_id}.jpg` + `{photo_id}.json` ✓
- Auth: hardcoded constants (older pattern — needs dotenv)
- No EXIF fetching

### `flickr_gallery_download.py` (uploaded, changes applied ✓, syntax error fixed)
- Downloads specific galleries (by URL or ID) or all your galleries
- Per-gallery subfolders: `./flickr_downloads/galleries/{slug}/`
- Fetches EXIF/IPTC data ✓
- Uses dotenv for credentials ✓
- Filenames: `{photo_id}{ext}` + `{photo_id}.json` ✓
- Has `slugify()` for folder names

These two are **complementary, not duplicates**. Neither supersedes the other.

---

## Bigger refactor: planned but not started

The conversation got to a clear architectural plan. Capture it here so it doesn't get lost.

### Proposed structure

```
md-flickr-tools/
  flickr/
    __init__.py
    auth.py          # OAuth, token caching, dotenv
    api.py           # all flickrapi calls (getInfo, getSizes, getExif, galleries, favourites)
    meta.py          # license map, date granularity, EXIF tag map, medium hints
    tags.py          # split_tags(), parse machine/RDF tags, clean human tags
  meta_formats/
    __init__.py
    harvard.py       # citation_markdown string (Harvard-adjacent)
    tasl.py          # TASL attribution line
    annotation.py    # Eagle YAML annotation block
    frontmatter.py   # Obsidian YAML frontmatter
  schema/
    fields.md        # canonical field reference — every field, provenance, crosswalk
    mapping.py       # machine-readable field translation dicts
  eagle_import.py    # thin wrapper, imports from flickr/ and meta_formats/
  fix_filenames.py
  flickr_favourites_download.py   # renamed from flickr_download.py
  flickr_gallery_download.py
  # future:
  # flickr_photostream_download.py
  # flickr_albums_download.py
```

### Key things to harmonise between the two download scripts
- `flickr_download.py` → add dotenv auth, add EXIF fetching
- `flickr_gallery_download.py` → add medium detection (MEDIUM_HINTS), add proper Harvard citations + TASL
- Harmonise license name format (one uses short "CC BY 2.0", other uses long form)
- Both should import shared code from `flickr/` rather than duplicating

### Tag cleansing (flickr/tags.py)
`split_tags()` currently lives in `eagle_import.py` but belongs in `flickr/tags.py` — it's about Flickr's data, not Eagle's. Machine tags (`bookid:`, `dc:identifier=`, `taxonomy:binomial=`) should be split out before metadata reaches any formatter.

The BHL (Biodiversity Heritage Library) machine tags are particularly rich:
`bookid:encyclopdiedhi10chens`, `bookauthor:Chenu_Jean_Charles_1808_1879`, `bookleafnumber:151` etc.
These are essentially a bibliographic record — the `bookid` is an Internet Archive identifier.
**Future work**: parse these into structured book metadata, cross-reference via IA API + Wikidata.
Relevant to dt-knowledge-base work.

### Schema crosswalk (schema/fields.md)
There is existing thinking on this in Obsidian — read these before designing the crosswalk:
- `_development-notes/md-pkim-library/Images and Collection Data - standards schema and formats.md`
- `md-pkim-library/README-extract-book-metadata.md`
- `_development-notes/md-pkim-library/museum-image-citation-structured-data-audit-handoff.md`
- `dt-knowledge-base/knowledge-base/artists/lod-lookup.yaml`

The internal sidecar schema should align to Dublin Core as the hub — DC has crosswalks to/from schema.org, Wikidata, MARC, Europeana, VRA Core (images), MET API etc. Design the `schema/fields.md` crosswalk table after reading the above notes.

---

## Immediate next steps (in order)

1. **Run `fix_filenames.py`** against the Eagle library and existing Flickr downloads to fix what's on disk now
2. **Apply the one-line patch** to `eagle_import.py` (`name = meta.get("photo_id")`)
3. **Read the Obsidian schema notes** before touching `schema/fields.md`
4. Then: scaffold the shared library structure above

---

## Files in this folder to commit to the repo
- `fix_filenames.py`
- `flickr_download.py` (updated)
- `flickr_gallery_download.py` (updated)
- `HANDOFF-flickr-eagle-refactor.md` (this file)
- `flickr_download_safe_filename_patch.py` (can delete once patches are applied)
- `eagle_import_patch.py` (can delete once patches are applied)
