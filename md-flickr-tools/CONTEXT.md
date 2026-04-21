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

Two citation formats are pre-built into every JSON file:

**Harvard-adjacent:**
```
Author (yyyy). _Title_. [Medium]. Institution, Location. Available at [URL](URL) (Accessed dd mmm yyyy). Licensed under [Licence](url).
```

**TASL:**
```
[Title](page url) — [Author](profile url) — [Licence](url)
```

### HTML in descriptions

Flickr descriptions can contain HTML with links and structured content. Decision: preserve as-is, label with `description_format: "html"`. Do not strip. Anything consuming the JSON should check `description_format` to decide whether to render or display as plain text.

### Tags

Stored as an array (not a space-separated string) for ease of downstream processing.

### Image sizing

Largest available up to X-Large 3K (3072px on longest side). Falls through gracefully if the owner has restricted downloads. Size label is stored in `size_label` so you know what you got.

### Flickr API notes

- All API data is UTF-8 encoded
- `taken` date is always in the owner's local timezone — do not convert
- `posted` date is always a UTC Unix timestamp
- `takengranularity`: 0=exact datetime, 4=month precision, 6=year precision, 8=circa
- Location is only returned if the photographer made it public
- `photos.getInfo` and `photos.getSizes` are called once per unique photo — these are the expensive calls

### Rate limiting

`RATE_DELAY = 0.5` seconds between API calls. Increase if hitting errors on large collections.

### Manifest

`_manifest.json` in the output folder tracks downloaded photos by ID. Re-runs skip anything in the manifest. `--reset` flag deletes the manifest. The manifest is gitignored (it lives alongside the downloaded files).

## Repo structure (intended)

```
md-flickr-tools/          # or a broader md-image-tools suite name
  flickr_download.py
  .env                    # never committed
  .env.example            # committed, with placeholder values
  .gitignore
  README.md
  TODO.md
  CONTEXT.md              # this file
  flickr_downloads/       # gitignored
```

## Tools / integrations on the roadmap

- **Are.na** — Kim is already connected to the Are.na API via Claude. Need to map JSON schema to Are.na block fields.
- **Obsidian** — generate `.md` files with YAML frontmatter from JSON. Kim has existing Pinterest → markdown work to align with.
- **Eagle** — image management app. Need to investigate Eagle's import format and whether citation JSON can be attached to items.
- **Keynote** — generate citation/reference slides from JSON data. Image + title + creator + citation + TASL.
- **Source shims** — The Met has a good public API. Tate has an API. Wikimedia Commons has an API. Google Arts & Culture is harder (likely scraping). ArtUK TBD.

## Secrets / API key management

Decision pending: standardise on `.env` + `python-dotenv`. Currently API keys are hardcoded in the script — this must be fixed before any public repo push. Single shared `.env` at suite root vs per-tool `.env` TBD.

## Related work

Kim has existing work on:
- Pinterest image downloads with markdown output
- Python invoice processing scripts (versioned, with changelogs, dry-run modes)
- Bulk PDF download automation

The metadata schema and markdown output patterns from the Pinterest work should be reviewed for alignment before building the Obsidian integration.
