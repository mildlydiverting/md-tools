# Handoff: dezoomify-alfred — v1.2 scraping fallback + upstream contribution

## Context
- **Repo**: not yet pushed to GitHub (files live in Alfred workflow folder)
- **Workflow folder**: `~/Library/CloudStorage/Dropbox/cross-machine-preferences/alfred/alfred preference sync/Alfred.alfredpreferences/workflows/user.workflow.190FB249-DD4B-406E-A65C-9021546D6424/`
- **Files being worked on**: `dezoomify_save.py` (v1.2), `get_browser_info.js` (v1.0), `test_dezoomify_workflow.zsh`
- **Current version**: v1.2

## What we built this session

Added an **HTML scraping fallback layer** to `dezoomify_save.py`. When dezoomify-rs can't auto-detect a tiled image from the page URL (error contains "none succeeded"), the script now:

1. Fetches the page HTML via `urllib` (with Safari User-Agent)
2. Runs site-specific scrapers to extract candidate tile URLs
3. Falls back to generic pattern matching if no site-specific hits
4. If one candidate: retries dezoomify-rs automatically
5. If multiple candidates: shows a macOS choose-from-list dialog
6. Records the actual URL used in the JSON metadata sidecar (`tile_url` field)

### Site-specific scrapers implemented

| Site | Format | What it extracts | Tested? |
|---|---|---|---|
| National Gallery (London) | IIPImage/IIIF | TIFF path → IIIF info.json URL | ⚠️ Regex tested against known tile URL; needs live test |
| Rijksmuseum | Micrio/IIIF | Micrio ID → iiif.micr.io info.json | ❌ Not yet tested |
| NGV | Zoomify | Zoom URL → ImageProperties.xml | ❌ Not yet tested |

### Generic patterns (fallback)
- IIIF info.json URLs
- IIIF manifest.json URLs
- DeepZoom .dzi files
- Zoomify ImageProperties.xml
- IIPImage FIF= URLs

### Key finding: National Gallery tile format
The NG uses IIPImage serving via the **IIIF Image API** (not DeepZoom as earlier GitHub issues suggested). The tile URL Kim captured from the Turner painting (NG508):

```
https://www.nationalgallery.org.uk/server.iip?IIIF=/fronts/N-0508-00-000032-XL-PYR.tif/23552,14336,1024,1024/256,256/0/default.jpg
```

The constructed info.json URL for dezoomify-rs:
```
https://www.nationalgallery.org.uk/server.iip?IIIF=/fronts/N-0508-00-000032-XL-PYR.tif/info.json
```

The TIFF naming pattern is `N-{accession}-00-{sequence}-{quality}-PYR.tif` in `/fronts/`. Quality codes seen: `XL` (current), `WZ` (2016 era). The 6-digit sequence varies per painting.

## Known issues / deferred things

- **NG scraper needs live testing**: The regex patterns work against the known tile URL string, but we haven't confirmed what the TIFF path looks like in the actual page HTML source. Kim needs to View Source on the painting page and search for `server.iip` or `.tif` to confirm where the path appears. It might be in a JS object, a `data-*` attribute, or an inline `<script>` block.
- **NG may block urllib fetch**: The page returned 403 to Claude's web_fetch tool. The scraper uses a Safari User-Agent header which may help, but needs testing.
- **Rijksmuseum not yet tested**: Need to save a Rijksmuseum page source and verify the Micrio ID extraction regex.
- **NGV not yet tested**: Same — need a live page.
- **No Eagle integration yet**: `eagle_item_id` field still `null` placeholder.
- **Not yet pushed to git**: Should go in `mildlydiverting/md-tools` or a new repo.

## What to do next session

### Priority 1: Live testing
1. Test the NG scraper against the Turner page — either:
   - Run the workflow from Alfred against `https://www.nationalgallery.org.uk/paintings/joseph-mallord-william-turner-ulysses-deriding-polyphemus-homer-s-odyssey`
   - Or run `dezoomify_save.py` manually from Terminal with env vars set
2. If the NG page returns 403 to urllib, try adding the page's `Referer` header, or use the `-H "Referer: ..."` flag in the dezoomify-rs command
3. Check whether the TIFF path is in the static HTML at all, or only loaded via JS (if JS-only, we may need to extract it from an API endpoint instead)

### Priority 2: Test other sites
- Rijksmuseum: `https://www.rijksmuseum.nl/en/collection/object/Nude-Woman-Lying-on-a-Pillow--6af483682af3df3a835a526f7beb07f3`
- NGV: `https://www.ngv.vic.gov.au/explore/collection/work/3867/`

### Priority 3: Upstream contribution planning
We want to contribute a National Gallery dezoomer to `lovasoa/dezoomify-rs`.

**Architecture notes** (from DeepWiki analysis of the codebase):
- Each dezoomer implements the `Dezoomer` trait: `name()` returns an identifier string, `zoom_levels()` processes a `DezoomerInput` (URI + page contents) and returns `ZoomLevels`
- The GAC dezoomer is the closest model: it fetches the page HTML, regex-extracts a base URL + token, fetches tile metadata XML, then generates zoom levels
- The NG dezoomer would: recognise `nationalgallery.org.uk/paintings/` → fetch HTML → extract TIFF path → construct IIIF info.json URL → delegate to the existing IIIF dezoomer
- Source lives in `src/` with one folder per dezoomer (e.g. `src/google_arts_and_culture/`)
- New dezoomer must be registered in `all_dezoomers()` in `src/auto.rs`
- dezoomify-rs is Rust; the Python scraper serves as a prototype to validate the patterns before porting

**Steps to contribute:**
1. Validate the scraping patterns with the Python prototype (this session's work)
2. File an issue on `lovasoa/dezoomify-rs` proposing the NG dezoomer (gauge interest, ask about architecture preferences)
3. Write the Rust implementation using the GAC dezoomer as a template
4. Submit PR with tests

**Key source files to study:**
- `src/google_arts_and_culture/mod.rs` — page scraping + dezoomer impl
- `src/google_arts_and_culture/tile_info.rs` — regex extraction of page info
- `src/dezoomer.rs` — the `Dezoomer` trait definition
- `src/auto.rs` — auto-detection logic and dezoomer registration
- DeepWiki docs: https://deepwiki.com/lovasoa/dezoomify-rs/2.2-dezoomer-framework

## Relevant technical constraints or decisions already made
- dezoomify-rs flags: `-l` (largest), `stdin=subprocess.DEVNULL` (no hang)
- Scraper uses stdlib only: `urllib.request`, `re` — no external dependencies
- `_fetch_html()` uses Safari User-Agent to avoid simple bot blocks
- Site-specific scrapers run before generic patterns (more reliable)
- Metadata sidecar now has `tile_url` field (null if page URL worked directly)
- Python is at `/usr/local/Cellar/python@3.14/`

## Test pages

| Site | URL | Expected format |
|---|---|---|
| National Gallery | https://www.nationalgallery.org.uk/paintings/joseph-mallord-william-turner-ulysses-deriding-polyphemus-homer-s-odyssey | IIPImage/IIIF |
| Rijksmuseum | https://www.rijksmuseum.nl/en/collection/object/Nude-Woman-Lying-on-a-Pillow--6af483682af3df3a835a526f7beb07f3 | Micrio/IIIF |
| NGV | https://www.ngv.vic.gov.au/explore/collection/work/3867/ | Zoomify |
| Google Arts & Culture | https://artsandculture.google.com/asset/horse-study-after-george-stubbs-anatomy-of-the-horse-clara-drummond/IQHEEIRr5uvO7A | GAC (works directly, no scraper needed) |
| Met Museum | https://www.metmuseum.org/art/collection/search/435809 | Unknown — investigate |
| Tate | https://www.tate.org.uk/art/artworks/johnson-young-man-in-green-t16376 | Unknown — investigate |

## Files to attach to next chat
- [ ] Current `dezoomify_save.py` (v1.2)
- [ ] Current `get_browser_info.js` (v1.0)
- [ ] Current `test_dezoomify_workflow.zsh`
- [ ] This handoff note
- [ ] Saved HTML of a failing page (NG painting page) for offline scraper testing

---
*Template: ~/Development/are.na-toolkit/handoff-template.md*
