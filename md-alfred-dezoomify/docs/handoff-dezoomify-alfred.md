# Handoff: dezoomify-alfred — v1.2 scraping fallback

## Context
- **Repo**: `mildlydiverting/md-tools/md-alfred-dezoomify` (or wherever Kim has put it)
- **Files being worked on**: `dezoomify_save.py` (v1.2), `get_browser_info.js` (v1.0), `test_dezoomify_workflow.zsh`
- **Current version**: v1.2

## What we built this session

Added an HTML scraping fallback to `dezoomify_save.py`. The pipeline is now:

1. **Try direct** (30s timeout): pass page URL to dezoomify-rs
2. **Scrape fallback** (600s timeout): fetch HTML, extract tile URLs, try each candidate in sequence
3. **Manual paste** (600s timeout): show dialog for user to paste a URL from dev tools

**National Gallery (London) is confirmed working end-to-end** — both command line and Alfred. The scraper finds the IIPImage TIFF path in the static HTML, constructs the `FIF=` URL, and dezoomify-rs downloads the tiles.

Key technical findings:
- The NG uses IIPImage serving IIIF v3 tiles. The info.json declares `maxWidth: 800` but tiles are 256×256
- The scraper produces IIPImage `FIF=` URLs (confirmed working) and DeepZoom `.dzi` URLs as fallback
- The NG serves IIIF manifests at `{painting_url}?altTemplate=PaintingManifest&zoomImageType=Front&layout=banner`
- The Turner (NG508) is 47,628 × 31,126 px = 1.48 GP, ~22,800 tiles — needs `max_megapixels` or a long timeout
- `-l` and `--max-width` are mutually exclusive in dezoomify-rs — fixed in `build_dezoomify_cmd()`
- dezoomify-rs won't overwrite files — script now cleans up partials between retries
- alfred.app expects a script environment variable `alfred_workflow_cache` for volatile files

## Known issues

### Rijksmuseum picks up wrong Micrio IDs
The "Discover more" section on each artwork page shows thumbnails of related works, all using `iiif.micr.io/{ID}/...` URLs. The scraper regex `iiif\.micr\.io/([A-Za-z0-9]{4,8})` matches these instead of the main artwork's viewer.

**Fix needed**: look for the `<micr-io id="...">` custom HTML element first (this is Micrio's viewer component). That element's `id` attribute contains the correct Micrio ID for the main artwork. Only fall back to `iiif.micr.io/` URL scraping if no `<micr-io>` element is found.

**Reference**: Micrio embedding docs at https://doc.micr.io/client/embedding.html

### NGV not yet tested

### NG manifest URL not yet used by scraper
The manifest contains rich metadata (dimensions, download URL, licence URL, canvas info). Currently unused — the scraper just extracts the TIFF path. Could be valuable for the metadata sidecar.

## What to do next session
See the todo list (separate file).

## Relevant technical constraints
- dezoomify-rs flags: `-l` = largest (when no size cap), `--max-width`/`--max-height` when `max_megapixels` is set
- Scraper uses stdlib only: `urllib.request`, `re`
- `_fetch_html()` uses Safari User-Agent to avoid bot blocks
- Site-specific scrapers run before generic patterns
- Candidates are tried in sequence; cleanup between attempts
- Metadata sidecar has `tile_url` field (null if page URL worked directly)
- Python 3.14.4 at `/usr/local/Cellar/python@3.14/`

## Files to attach to next chat
- [ ] Current `dezoomify_save.py` (v1.2)
- [ ] Current `get_browser_info.js` (v1.0)
- [ ] This handoff note

---
*Template: ~/Development/are.na-toolkit/handoff-template.md*
