# Context notes

Notes for continuity across sessions — for Kim and for Claude.

## What this project is

A suite of tools for downloading and archiving images from online sources (starting with Flickr), with structured metadata designed for:

- Proper citation in teaching, writing, and presentations
- Import into tools like Obsidian, Eagle, Are.na, Keynote
- Long-term archiving with enough context to know what something is and where it came from
- Eventually: source-agnostic schema that works across Flickr, museum APIs, Wikimedia etc.

## Kim's context

Kim is an artist and drawing teacher based in East Kent. She uses reference images extensively in her teaching practice and personal work. She has a strong background in digital/media production and content strategy, and is comfortable with technical tools. Her practice emphasises accessibility, proper attribution, and working generously with source material.

## Scripts in this suite

| Script | Status | Notes |
|---|---|---|
| `flickr_download.py` | ✅ Working | Downloads Flickr favourites with JSON sidecars |
| `flickr_gallery_download.py` | ✅ Working | Downloads Flickr galleries with JSON sidecars |
| `eagle_import.py` | ✅ Working | Imports image+sidecar pairs into Eagle via Web API v2 |
| `flickr_fix_citations.py` | ✅ Working | Backfills/fixes `citation_markdown` + `tasl` in existing sidecars |

## Design decisions made so far

### Metadata schema

The JSON schema is designed to be source-agnostic from the start, even though we're only building Flickr first. Fields like `institution`, `institution_location`, `website`, `website_url` are present but null for most Flickr photos — they exist because they'll be populated for museum sources like The Met or Tate.

Key fields and why:

- `accessed_url` — the permalink/page URL (what you'd put in a citation)
- `src_url` — the direct image file URL (not the same thing)
- `date_created` — when the work was made (for photos: EXIF date taken, owner's local timezone, do not convert)
- `date_created_granularity` — Flickr integer (0=exact, 4=month, 6=year, 8=circa)
- `date_posted` — when it was uploaded to the platform (UTC)
- `date_accessed` — full ISO 8601 UTC timestamp of download
- `medium` — defaults to Photograph for Flickr, inferred from tags, will vary for museum sources
- `description_format` — `html` or `text`; descriptions are stored as-is, not stripped
- `institution` — the legal/physical owner of the work (a museum, archive etc), NOT the platform
- `website` — the platform (Flickr, The Met website, etc.)
- `citation_markdown` — pre-built Harvard-adjacent citation in Markdown
- `tasl` — pre-built TASL attribution line in Markdown (Title, Author, Source, License)

### Citation formats

Two citation formats are pre-built into every JSON sidecar:

**Harvard-adjacent:**
```
Author (yyyy). _Title_. [Medium]. Institution, Location. Available at [URL](URL) (Accessed dd mmm yyyy). Licensed under [Licence](url).
```

**TASL:**
```
[Title](page url) — [Author](profile url) — [Licence](url)
```

Both fields may need backfilling if sidecars were downloaded with an older version of the script (pre-June 2026) — use `flickr_fix_citations.py --recursive` for this.

### Eagle annotation format

The Eagle annotation field holds a YAML front matter block (for machine readability), followed by the plain-text citation (for human readability), followed by machine tags if present:

```
---
creator: ...
creator_url: ...
date_created: ...
medium: Photograph
license: ...
license_url: ...
source_url: ...
tasl: '...'
citation: ...
---

Plain text citation here.

tags:
  taxonomy:binomial=Phyllactinia guttata
  dc:identifier=http://...
```

### Machine tags

Flickr (and especially BHL/biodiversity images) can carry hundreds of machine tags in `namespace:value` format — `bookid:`, `taxonomy:`, `dc:`, `bhl:`, `geo:`, `sherlocknet:`, `artist:`, etc. These are:
- **Excluded** from Eagle's tags field (keeps tags clean for human use)
- **Appended** to the annotation block under a `tags:` section (preserves the data)

The filter rule: any tag matching `\w+:.+` is a machine tag.

### HTML in descriptions

Flickr descriptions can contain HTML. Decision: preserve as-is, label with `description_format: "html"`. Do not strip. Anything consuming the JSON should check `description_format`.

### Tags

Stored as an array (not a space-separated string). `tags_normalised` is explicitly out of scope for all importer scripts — it will be a future standalone cross-platform tag normalisation tool.

### Image sizing

Largest available up to X-Large 3K (3072px on longest side). Falls through gracefully if the owner has restricted downloads. Size label stored in `size_label`.

### Eagle import notes

- API endpoint: `POST /api/item/addFromPaths` (v1 API, port 41595)
- `folderId` is a top-level parameter on the payload, not per-item
- Folder create uses `{"folderName": "..."}` and returns `data` as a single object
- `addFromPaths` returns `{"status": "success"}` only — no item IDs. We write `eagle_imported: true` to the sidecar instead
- Image path must be absolute (use `Path.resolve()`)
- Eagle must be open and running before import

### Flickr API notes

- All API data is UTF-8 encoded
- `taken` date is always in the owner's local timezone — do not convert
- `posted` date is always a UTC Unix timestamp
- `takengranularity`: 0=exact datetime, 4=month precision, 6=year precision, 8=circa
- Location is only returned if the photographer made it public
- `photos.getInfo` and `photos.getSizes` are called once per unique photo

### Rate limiting

`RATE_DELAY = 0.5` seconds between API calls. Increase if hitting errors on large collections.

### Manifest

`_manifest.json` / `_gallery_manifest.json` in each output folder tracks downloaded photos by ID. Re-runs skip anything in the manifest. `--reset` flag deletes the manifest. Manifests are gitignored.

## Repo structure

```
md-flickr-tools/
  flickr_download.py
  flickr_gallery_download.py
  eagle_import.py
  flickr_fix_citations.py
  .env                    # never committed
  .env.example            # committed, with placeholder values
  .gitignore
  README.md
  TODO.md
  CONTEXT.md              # this file
  metadata-mapping.md
  flickr_downloads/       # gitignored
```

## Tools / integrations on the roadmap

- **Are.na** — map JSON schema to Are.na block fields; write `arena_upload.py`
- **Obsidian** — generate `.md` files with YAML frontmatter from JSON sidecars
- **Eagle inspector plugin** — display and write-back attribution YAML for selected Eagle items; started in earlier session (blank window bug — likely manifest config issue)
- **Keynote** — generate citation/reference slides from JSON data
- **Source shims** — The Met (good public API), Tate (API), Wikimedia Commons (API), Google Arts & Culture (likely scraping), ArtUK (TBD)

## Secrets / API key management

`.env` + `python-dotenv`. API keys go in `.env` (gitignored). Flickr OAuth token cached at `~/.flickr/`. venv at `/Users/kimplowright/Development/bins/`.
