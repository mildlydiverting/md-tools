# md-flickr-tools

A Python script for downloading images from your Flickr favourites and galleries, with structured JSON metadata designed for archiving, citation, and future import into other tools.

## What it does

- Authenticates with Flickr via OAuth
- Fetches all your favourited photos
- Fetches all your galleries and the photos within them
- Deduplicates across favourites and galleries (downloads once, records all occurrences)
- Downloads the largest available image up to ~3K (3072px on longest side), respecting owner restrictions
- Saves a JSON metadata file alongside each image with full citation data
- Maintains a manifest so re-runs skip already-downloaded images
- Supports `--reset` to re-download everything from scratch

## Requirements

```bash
pip install flickrapi requests
```

Python 3.12+ recommended.

## Setup

1. Get a Flickr API key at https://www.flickr.com/services/apps/create/ (non-commercial)
2. Copy `.env.example` to `.env` and fill in your API key and secret (see [API keys](#api-keys))
3. Run the script — on first run you'll be directed to a URL to authorise access, then asked to paste back a verifier code
4. The OAuth token is cached at `~/.flickr/` after first auth — it won't ask again

## Usage

```bash
# Normal run — skips already-downloaded images
python flickr_download.py

# Re-download everything from scratch
python flickr_download.py --reset
```

## Output

Files are saved to `./flickr_downloads/` (configurable via `OUTPUT_DIR`). Each photo produces two files:

```
flickr_downloads/
  55186319833_Artemis II Launch.jpg
  55186319833_Artemis II Launch.json
  _manifest.json
```

### JSON metadata structure

```json
{
  "photo_id": "55186319833",
  "title": "Artemis II Launch (NHQ202604010115)",
  "accessed_url": "https://www.flickr.com/photos/35067687@N04/55186319833",
  "src_url": "https://live.staticflickr.com/..._3k.jpg",
  "size_label": "X-Large 3K",
  "date_created": "2026-04-01",
  "date_created_granularity": 0,
  "date_created_note": "Exact datetime (owner's local timezone — do not convert)",
  "date_posted": "2026-04-04",
  "date_accessed": "2026-04-21T12:11:53.614686Z",
  "medium": "Photograph",
  "description": "...",
  "description_format": "html",
  "tags": ["nasa", "artemis", "kennedy"],
  "occurrences": [
    { "type": "favourite" },
    { "type": "gallery", "gallery_id": "...", "gallery_title": "Space" }
  ],
  "location": {
    "latitude": "28.5728",
    "longitude": "-80.6490",
    "locality": "Merritt Island",
    "region": "Florida",
    "country": "United States"
  },
  "creator": "NASA HQ PHOTO",
  "creator_profile_url": "https://www.flickr.com/photos/35067687@N04/",
  "institution": null,
  "institution_location": null,
  "website": "Flickr",
  "website_url": "https://www.flickr.com",
  "license_id": "8",
  "license_name": "United States Government Work",
  "license_url": "http://www.usa.gov/copyright.shtml",
  "copyright_line": null,
  "citation_markdown": "NASA HQ PHOTO (2026). _Artemis II Launch_. [Photograph]. Available at [...] (Accessed 21 Apr 2026). United States Government Work.",
  "tasl": "[Artemis II Launch](...) — [NASA HQ PHOTO](...) — United States Government Work"
}
```

#### Citation fields

The metadata is designed for future citation use across multiple platforms (Flickr, The Met, Tate, Wikimedia Commons, Google Arts & Culture, ArtUK etc). The schema aims to be source-agnostic:

| Field | Notes |
|---|---|
| `date_created` | Date photo was taken (owner's local timezone — do not convert) |
| `date_created_granularity` | 0=exact, 4=month, 6=year, 8=circa |
| `date_posted` | UTC date uploaded to Flickr |
| `date_accessed` | UTC ISO timestamp of download |
| `medium` | Inferred from tags; defaults to `Photograph` |
| `institution` | Physical/legal owner of the work (e.g. Tate, The Met) — null for most Flickr photos |
| `description_format` | `html` or `text` — descriptions may contain markup, stored as-is |

## Flickr API methods used

| Method | Purpose |
|---|---|
| `flickr.test.login` | Confirm auth, retrieve user ID |
| `flickr.favorites.getList` | Fetch all favourited photos |
| `flickr.galleries.getList` | Fetch all galleries |
| `flickr.galleries.getPhotos` | Fetch photos within a gallery |
| `flickr.photos.getInfo` | Per-photo: dates, license, owner, location |
| `flickr.photos.getSizes` | Per-photo: available download sizes |

Note: `getInfo` and `getSizes` are called once per unique photo. Rate delay is set to 0.5s between calls — increase `RATE_DELAY` if you hit errors on large collections.

## API keys

Never commit API keys to git. See `.env.example` and use `python-dotenv` to load them. Your Flickr OAuth token is cached at `~/.flickr/` (your home directory) — it is not in the repo.

## Notes

- All data is UTF-8 encoded, as required by the Flickr API
- Location data is only present if the photographer made it public
- Image size falls back gracefully if the owner has restricted downloads
- Tags are stored as an array for ease of processing
- HTML in description fields is preserved as-is and labelled with `description_format: "html"`

## Part of a larger suite

This tool is intended to be one of several source-specific scripts sharing a common metadata schema. Planned additions: The Met, Tate, Wikimedia Commons, Google Arts & Culture, ArtUK, Pinterest.
