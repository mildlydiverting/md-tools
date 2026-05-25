# Handoff: md-flickr-tools — Flickr gallery downloader + metadata mapping

## Context
- **Repo**: https://github.com/mildlydiverting/md-tools (subfolder: `md-flickr-tools/`)
- **File(s) being worked on**: `flickr_gallery_download.py`
- **Current version**: v1.0 (new script, not yet committed)
- **Related files produced this session**: `metadata-mapping.md` (canonical schema reference)

## What we built this session

A new standalone script `flickr_gallery_download.py` that downloads images from Flickr galleries with full structured JSON metadata sidecars. It handles authentication via OAuth (shared with `flickr_download.py`), downloads at the best available size (capped at 3K), and outputs to `./flickr_downloads/galleries/[gallery-title-slug]/`. Each gallery gets a `_gallery_manifest.json` for skip-on-rerun deduplication. The script also calls `flickr.photos.getExif` and captures selected EXIF and IPTC fields (camera, lens, exposure, mandatory credit, transmission reference/accession number) into an `exif` sub-object in the JSON sidecar. A canonical metadata mapping document (`metadata-mapping.md`) was also drafted, covering source mappings (Flickr, Wikimedia Commons, AIC, BM/Harvard, Are.na, museum APIs) and destination mappings (Eagle, Are.na, Obsidian, Pinboard), with schema.org alignment and Wikidata enrichment paths noted.

## Known issues / deferred things

- **TASL format needs fixing**: current implementation has Title and Source collapsed into one linked element rather than proper four-part Title / Author / Source / Licence structure. Fix in both `flickr_download.py` and `flickr_gallery_download.py` at the same time. Reference: https://wiki.creativecommons.org/wiki/best_practices_for_attribution
- **Eagle import script not yet written**: the next concrete step is `eagle_import.py` — reads a gallery folder of image+JSON pairs and imports into Eagle via Web API v2 (`localhost:41595`), mapping fields per the destination mapping table, with annotation as YAML block
- **Eagle inspector plugin**: started in a previous session (md-ember-to-eagle), showed blank window. Needs revisiting to display and write-back attribution YAML from the JSON sidecar. Plugin API confirmed: `eagle.item.getSelected()` + `item.save()` supports reading/writing `annotation` and `tags`.
- **`tags_normalised` deliberately omitted**: will be handled by a separate standalone tag normalisation tool, not part of this script
- **`medium` and `dimensions` not available from Flickr API**: fields exist in canonical schema but will be null for Flickr sources; consider a manual enrichment pass
- **EXIF access is owner-controlled**: `get_exif()` returns `None` gracefully if disabled; this is expected behaviour for many non-professional photographers

## What I want to do next session

Primary: write `eagle_import.py` — takes a gallery download folder as input, checks Eagle is running, imports image+JSON pairs via `POST /api/v2/item/add`, maps metadata fields per the mapping table, stores Eagle item ID back into the JSON sidecar, and creates/assigns Eagle folders by gallery title.

Secondary: revisit the Eagle inspector plugin to display the attribution YAML block for a selected image.

## Relevant technical constraints and decisions already made

- **Separate scripts, loosely joined**: `flickr_gallery_download.py`, `eagle_import.py`, and future tools are independent scripts that communicate via the canonical JSON sidecar format — not monolithic. Each does one thing.
- **Canonical JSON sidecar is the interchange format**: all source adapters write to it; all destination adapters read from it. Schema defined in `metadata-mapping.md`.
- **Eagle Web API v2** (`localhost:41595/api/v2/`) — no auth needed for localhost. Confirmed working on Eagle 4.0 Build 21+. Batch import via `POST /api/v2/item/add` with `items` array.
- **Eagle annotation field holds the YAML attribution block** — no native custom fields in Eagle; annotation is the right place. YAML format chosen for human readability and parseability.
- **Eagle `btime` direct edit** (from ember handoff): Eagle must be closed before editing `metadata.json` directly; API-based import sets item date at import time only — `btime` workaround may be needed if original photo dates matter in Eagle
- **venv**: activate `/Users/kimplowright/Development/bins/bin/activate` before running; `flickrapi`, `requests`, `python-dotenv` must be installed there
- **Credentials**: `FLICKR_API_KEY` and `FLICKR_API_SECRET` in `.env` file alongside script; `.env` in `.gitignore`; OAuth token cached at `~/.flickr/` after first run
- **No `tags_normalised` in importer**: tag normalisation is a separate future tool

## Metadata mapping reference

Key Eagle field mappings from canonical JSON:

| Canonical field | Eagle field | Notes |
|---|---|---|
| `title` | `name` | |
| `source_url` | `website` | |
| `tags` | `tags` | Raw Flickr tags only for now |
| `gallery.title` | `folders` | Create/match folder by name |
| Full attribution block | `annotation` | YAML format (see below) |

YAML annotation block format:
```yaml
creator: NASA/Keegan Barber
creator_url: https://www.flickr.com/photos/nasahqphoto/
date_created: "2026-04-01"
medium: Photograph
license: CC BY-NC-ND 4.0
license_url: https://creativecommons.org/licenses/by-nc-nd/4.0/deed.en
source_url: https://www.flickr.com/photos/nasahqphoto/55181686977
copyright_line: "(NASA/Keegan Barber) For copyright and restrictions refer to http://www.nasa.gov/multimedia/guidelines/index.html"
tasl: "[Title](url) — [Creator](url) — Flickr — [CC BY-NC-ND 4.0](url)"
citation: "NASA/Keegan Barber (2026). _Title_. [Photograph]. Available at URL (Accessed 25 May 2026). CC BY-NC-ND 4.0."
accession_number: NHQ202604010102
```

## Files to attach
- [x] `flickr_gallery_download.py` (current working version)
- [x] `metadata-mapping.md` (canonical schema and mapping tables)
- [ ] `flickr_download.py` (existing script — for reference when fixing TASL)

---
*Template: ~/Development/are.na-toolkit/handoff-template.md*
