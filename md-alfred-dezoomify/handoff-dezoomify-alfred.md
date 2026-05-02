# Handoff: dezoomify-alfred — HTML scraping fallback + next steps

## Context
- **Repo**: not yet pushed to GitHub (files live in Alfred workflow folder)
- **Workflow folder**: `~/Library/CloudStorage/Dropbox/cross-machine-preferences/alfred/alfred preference sync/Alfred.alfredpreferences/workflows/user.workflow.190FB249-DD4B-406E-A65C-9021546D6424/`
- **Files being worked on**: `dezoomify_save.py` (v1.1), `get_browser_info.js` (v1.0), `test_dezoomify_workflow.zsh`
- **Current version**: v1.1

## What we built last session

A working Alfred workflow that:
- Detects frontmost browser (Safari or Chrome) via JXA, grabs URL + page title
- Captures selected text via Alfred hotkey clipboard trick
- Runs dezoomify-rs on the URL with `-l` flag (largest zoom level, non-interactive)
- Shows a macOS filename dialog with a smart suggestion (parses "Title: X" / "Creator: X" from selected text, strips site names from page titles, falls back to domain+datetime)
- Saves image + JSON sidecar with full metadata (dimensions via sips, file size, dezoomify-rs version, eagle_item_id placeholder)

**Confirmed working**: Google Arts & Culture page URLs. The workflow is end-to-end functional for sites where dezoomify-rs can detect the tiled image directly from the page URL.

## Known issues / deferred things

- **Rijksmuseum fails**: Uses Micrio (iiif.micr.io) for image delivery. The short Micrio ID (e.g. `PJEZO`) is embedded in the page JS but not in the collection page URL. dezoomify-rs can't detect it from the page URL alone. The correct URL to pass dezoomify-rs is `https://iiif.micr.io/{ID}/info.json` — but you need to find the ID first.
- **NGV works if you pass the right URL**: The Zoomify XML path (`https://content.ngv.vic.gov.au/col-images/zooms/{ID}/ImageProperties.xml`) works, but dezoomify-rs can't construct it from the collection page URL. The ID (`Fd104934` etc.) is in the page source as `var url = 'https://content.ngv.vic.gov.au/col-images/zooms/{ID}/'` inside an `ol.source.Zoomify` block.
- **GAC images are small**: Google Arts & Culture intentionally restricts resolution regardless of zoom level flag. This is a Google-imposed limit, not a workflow bug.
- **No interactive zoom level selection**: Currently always uses `-l` (largest). User can't choose a specific level. Deferred.
- **No Eagle integration**: `eagle_item_id` field in JSON sidecar is `null` placeholder. Deferred.
- **Not yet pushed to a git repo**: Should go in `mildlydiverting/md-tools` or a new `mildlydiverting/dezoomify-alfred` repo.

## What to do next session: HTML scraping fallback

### The problem
dezoomify-rs is given the collection page URL. For sites like Rijksmuseum and NGV, the tiled image viewer is loaded dynamically with a secondary ID that doesn't appear in the page URL. dezoomify-rs tries the page URL, finds no tiled image format, and fails.

### The solution: a Python HTML scraper
When dezoomify-rs fails with "none succeeded", fetch the page HTML and search for known patterns. This is modelled on dezoomify (web version)'s dezoomer architecture — each dezoomer has a `contents` regex that matches page source.

**Patterns to implement (in order of priority):**

| Format | Pattern to find in HTML | URL to pass dezoomify-rs |
|---|---|---|
| Micrio/IIIF (Rijksmuseum) | `iiif.micr.io/([A-Za-z0-9]+)` | `https://iiif.micr.io/{ID}/info.json` |
| Zoomify (NGV etc.) | `ol\.source\.Zoomify.*?url.*?['"]([^'"]+)['"]` | `{url}ImageProperties.xml` |
| Generic IIIF manifest | `(https?://[^'"]+/manifest\.json)` | the manifest URL directly |
| DeepZoom DZI | `(https?://[^'"]+\.dzi)` | the DZI URL directly |
| Generic info.json | `(https?://[^'"]+/info\.json)` | the info.json URL directly |

**Logic to add to `dezoomify_save.py`:**

```python
def scrape_tile_url(page_url: str) -> list[str]:
    """Fetch page HTML and extract candidate tiled image URLs.
    Returns a list of candidate URLs to try with dezoomify-rs."""
    # fetch HTML (urllib, no dependencies)
    # apply regex patterns above
    # return deduplicated list of candidates

def try_dezoomify(url, output_path, ...):
    """Run dezoomify-rs; return (success, error_string)"""

# In main():
# 1. Try page URL directly
# 2. If fails with "none succeeded", call scrape_tile_url(URL)
# 3. If one candidate: retry automatically, show alert if that also fails
# 4. If multiple candidates: show osascript choose-from-list dialog
# 5. If no candidates: show dialog asking user to paste URL manually
```

### Key research to do first
Before writing the scraper, read dezoomify's actual dezoomer source files to borrow their regex patterns:
- `https://github.com/lovasoa/dezoomify/tree/master` — look at the JS files in the root, each is a dezoomer
- `https://raw.githubusercontent.com/lovasoa/dezoomify/master/tests/test_urls.js` — comprehensive list of known-working URLs, good for testing
- The dezoomify-extension's `background.js` uses URL pattern matching (not HTML scraping), so it's less useful for our Python approach. Its pattern list is still worth reading for known tile URL signatures.

**Important distinction learned this session:**
- dezoomify-extension = network request interception (live browser, can't replicate in Python)
- dezoomify web app dezoomers = HTML source pattern matching (replicable in Python ✓)
- dezoomify-rs = tries its own detection from page URL, no HTML scraping fallback

** Sources of info **

https://dezoomify.ophir.dev
https://github.com/lovasoa/dezoomify
https://github.com/lovasoa/dezoomify/wiki
https://dezoomify-rs.ophir.dev
https://github.com/lovasoa/dezoomify-rs
https://github.com/lovasoa/dezoomify/issues?q=
https://lovasoa.github.io/dezoomify-extension/
https://github.com/lovasoa/dezoomify-extension
https://github.com/lovasoa/dezoomify/wiki/How-to-add-support-for-a-new-website

** potential test pages **

https://www.rijksmuseum.nl/en/collection/object/Nude-Woman-Lying-on-a-Pillow--6af483682af3df3a835a526f7beb07f3
https://artsandculture.google.com/asset/horse-study-after-george-stubbs-anatomy-of-the-horse-clara-drummond/IQHEEIRr5uvO7A
https://wellcomecollection.org/works/zs6gser7/images?id=c7hxpemj
https://www.ngv.vic.gov.au/explore/collection/work/3867/
https://www.metmuseum.org/art/collection/search/435809
https://www.tate.org.uk/art/artworks/johnson-young-man-in-green-t16376

### osascript choose-from-list for multiple candidates
```applescript
choose from list {"https://iiif.micr.io/ABC/info.json", "https://..."} 
  with title "Dezoomify Grab" 
  with prompt "Multiple tiled images found. Which to download?"
  default items item 1
```
Python: `subprocess.run(['osascript', '-e', script], ...)`

## Relevant technical constraints or decisions already made
- dezoomify-rs flags: `-l` (largest), `stdin=subprocess.DEVNULL` (no hang), `--max-width/--max-height` for size limiting
- Alfred env vars: `url`, `page_title`, `selected_text`, `save_folder`, `dezoomify_bin`, `image_format`, `max_megapixels`
- No frameworks: vanilla Python 3, stdlib only (`subprocess`, `json`, `re`, `urllib`, `pathlib`)
- JXA script outputs Alfred-format JSON: `{"alfredworkflow": {"arg": URL, "variables": {...}}}`
- Run Script step calling `get_browser_info.js` must use `< /dev/null` to stop selected text leaking into output
- `sips` used for image dimensions (ships with macOS, no Pillow needed)
- Python is at `/usr/bin/python3` (system) or `/usr/local/bin/python3` (Homebrew); workflow uses whichever `python3` resolves to
- Python 3.14.4 installed at `/usr/local/Cellar/python@3.14/`

## Files to attach to next chat
- [ ] Current `dezoomify_save.py` (v1.1)
- [ ] Current `get_browser_info.js`
- [ ] Current `test_dezoomify_workflow.zsh`
- [ ] This handoff note
- [ ] Saved HTML of a failing page (Rijksmuseum) if you want to test the scraper offline

---
*Template: ~/Development/are.na-toolkit/handoff-template.md*
