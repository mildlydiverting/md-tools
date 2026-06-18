# md-flickr-tools

Python scripts for downloading images from Flickr favourites and galleries, with structured JSON metadata designed for archiving, citation, and import into other tools.

## Scripts

| Script | Purpose |
|---|---|
| `flickr_download.py` | Download your Flickr favourites |
| `flickr_gallery_download.py` | Download images from your Flickr galleries |
| `eagle_import.py` | Import downloaded images + sidecars into Eagle |
| `flickr_fix_citations.py` | Backfill/fix `citation_markdown` and `tasl` in existing sidecars |

## Requirements

```bash
pip install flickrapi requests pyyaml python-dotenv
```

Python 3.12+ recommended. Activate the shared venv first:

```bash
source /Users/kimplowright/Development/bins/bin/activate
```

## Setup

1. Get a Flickr API key at https://www.flickr.com/services/apps/create/ (non-commercial)
2. Copy `.env.example` to `.env` and fill in your API key and secret
3. Run a download script — on first run you'll be directed to a URL to authorise access, then asked to paste back a verifier code
4. The OAuth token is cached at `~/.flickr/` after first auth

## Usage

### Download favourites

```bash
python flickr_download.py           # Normal run — skips already-downloaded images
python flickr_download.py --reset   # Re-download everything from scratch
```

### Download galleries

```bash
python flickr_gallery_download.py                           # All your galleries
python flickr_gallery_download.py --gallery-url URL         # Specific gallery by URL
python flickr_gallery_download.py --gallery-id GALLERY_ID   # Specific gallery by ID
python flickr_gallery_download.py --reset                   # Re-download everything
```

### Import into Eagle

Eagle must be open before running. No authentication needed — the API runs locally on port 41595.

```bash
python eagle_import.py flickr_downloads/_test --dry-run     # Preview without importing
python eagle_import.py flickr_downloads/_test               # Import a single folder
python eagle_import.py flickr_downloads/ --recursive        # Import all subfolders
```

Each image is imported with:
- **Name** — photo title
- **Website** — Flickr permalink
- **Tags** — human-readable tags only (machine tags excluded)
- **Folder** — created/matched from `gallery_title` in the sidecar (favourites are unfoldered)
- **Annotation** — YAML front matter block with full attribution, followed by plain-text citation; machine tags appended at the bottom

After import, `eagle_imported: true` is written back to the JSON sidecar. Subsequent runs skip already-imported items.

#### Reset the import flag

To re-import everything (e.g. after changing annotation format):

```bash
cd ~/Development/md-tools/md-flickr-tools
python3 -c "
import json, pathlib
for p in pathlib.Path('flickr_downloads').rglob('*.json'):
    if p.name.startswith('_'):
        continue
    m = json.load(open(p))
    if m.pop('eagle_imported', None) or m.pop('eagle_id', None):
        json.dump(m, open(p, 'w'), indent=2, ensure_ascii=False)
        print(f'Reset: {p}')
"
```

### Fix citations in existing sidecars

If sidecars were downloaded with an older version of the scripts, `citation_markdown` may have unlinked URLs. This script rebuilds both `citation_markdown` and `tasl` from the other sidecar fields:

```bash
python flickr_fix_citations.py flickr_downloads/ --recursive --dry-run   # Preview
python flickr_fix_citations.py flickr_downloads/ --recursive              # Apply
```

## Output

Files are saved to `./flickr_downloads/`. Favourites go directly into that folder; gallery downloads go into subfolders named after the gallery.

```
flickr_downloads/
  55186319833_Artemis II Launch.jpg
  55186319833_Artemis II Launch.json
  _manifest.json
  galleries/
    Public Domain Images 3/
      2919838443_Joseph Breintnall Nature Prints of Leaves.jpg
      2919838443_Joseph Breintnall Nature Prints of Leaves.json
      _gallery_manifest.json
```

### JSON sidecar structure

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
  "location": { "latitude": "28.57", "longitude": "-80.64", "locality": "Merritt Island", "region": "Florida", "country": "United States" },
  "creator": "NASA HQ PHOTO",
  "creator_profile_url": "https://www.flickr.com/photos/35067687@N04/",
  "institution": null,
  "website": "Flickr",
  "website_url": "https://www.flickr.com",
  "license_id": "8",
  "license_name": "United States Government Work",
  "license_url": "http://www.usa.gov/copyright.shtml",
  "copyright_line": null,
  "citation_markdown": "NASA HQ PHOTO (2026). _Artemis II Launch_. [Photograph]. Available at [https://...](https://...) (Accessed 21 Apr 2026). Licensed under [United States Government Work](http://www.usa.gov/copyright.shtml).",
  "tasl": "[Artemis II Launch](...) — [NASA HQ PHOTO](...) — [United States Government Work](...)"
}
```

### Eagle annotation format

The annotation field in Eagle contains a YAML front matter block followed by the plain-text citation and any machine tags:

```
---
creator: NASA HQ PHOTO
creator_url: https://www.flickr.com/photos/35067687@N04/
date_created: '2026-04-01'
medium: Photograph
license: United States Government Work
license_url: http://www.usa.gov/copyright.shtml
source_url: https://www.flickr.com/photos/35067687@N04/55186319833
tasl: '[Artemis II Launch](...) — [NASA HQ PHOTO](...) — [United States Government Work](...)'
citation: NASA HQ PHOTO (2026). _Artemis II Launch_. [Photograph]. Available at [...](...) (Accessed 21 Apr 2026).
---

NASA HQ PHOTO (2026). _Artemis II Launch_. [Photograph]. Available at [...](...) (Accessed 21 Apr 2026).

tags:
  bookid:dieforstinsekten02esch
  taxonomy:binomial=Phyllactinia guttata
  dc:identifier=http://biodiversitylibrary.org/page/16930610
```

Machine tags (anything matching `namespace:value`) are excluded from Eagle's tags field and appended to the annotation instead, keeping the tags list clean for human use.

## Flickr API methods used

| Method | Purpose |
|---|---|
| `flickr.test.login` | Confirm auth, retrieve user ID |
| `flickr.favorites.getList` | Fetch all favourited photos |
| `flickr.galleries.getList` | Fetch all galleries |
| `flickr.galleries.getPhotos` | Fetch photos within a gallery |
| `flickr.photos.getInfo` | Per-photo: dates, license, owner, location |
| `flickr.photos.getSizes` | Per-photo: available download sizes |
| `flickr.photos.getExif` | Per-photo: EXIF/IPTC fields (owner-controlled) |

`getInfo` and `getSizes` are called once per unique photo. Rate delay is 0.5s between calls — increase `RATE_DELAY` if you hit errors on large collections.

## API keys

Never commit API keys to git. Use `.env.example` as a template. Your Flickr OAuth token is cached at `~/.flickr/` and is not in the repo.

## Part of a larger suite

This is one of several source-specific scripts sharing a common metadata schema. Planned additions: The Met, Tate, Wikimedia Commons, Google Arts & Culture, ArtUK, Pinterest.
