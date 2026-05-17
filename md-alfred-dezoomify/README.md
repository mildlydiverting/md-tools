# dezoomify-alfred — v1.2

Alfred workflow to grab tiled images (IIIF, Zoomify, DeepZoom, IIPImage, etc.)
from the current browser tab using
[dezoomify-rs](https://github.com/lovasoa/dezoomify-rs).

Saves the full-resolution image plus a JSON metadata sidecar to a folder you
configure. Works with Safari and Chrome.

**v1.2 adds an HTML scraping fallback**: when dezoomify-rs can't auto-detect the
tiled image from the page URL (common on museum sites that load viewers via
JavaScript), the script fetches the page source and extracts tile URLs using
site-specific scrapers. Currently supports the National Gallery (London), with
Rijksmuseum and NGV in progress.

---

## Files

| File | Purpose |
|---|---|
| `get_browser_info.js` | JXA script — gets URL, page title, selected text |
| `dezoomify_save.py` | Python script — runs dezoomify-rs, scrapes tile URLs, prompts for filename, saves files |
| `bin/dezoomify-rs` | Optional: bundled binary (see below) |

---

## How it works

1. **Try direct**: passes the browser URL to dezoomify-rs, which tries all its
   built-in dezoomers (IIIF, Zoomify, DeepZoom, IIPImage, etc.)
2. **Scrape fallback**: if that fails, fetches the page HTML and runs
   site-specific scrapers to find tile URLs hidden in JavaScript
3. **Manual paste**: if scraping finds nothing, shows a dialog where you can
   paste a tile URL from the browser's Network Inspector
4. Saves the image + JSON metadata sidecar to your configured folder

---

## Dependencies

**dezoomify-rs** must be installed. Easiest via Homebrew:

```zsh
brew install dezoomify-rs
```

The Python script looks for it in this order:
1. `./bin/dezoomify-rs` inside the workflow folder (bundled)
2. `/opt/homebrew/bin/dezoomify-rs` (Homebrew, Apple Silicon)
3. `/usr/local/bin/dezoomify-rs` (Homebrew, Intel)
4. Anywhere on `$PATH`

To bundle the binary (makes the workflow portable / shareable):
```zsh
mkdir -p ~/path/to/workflow/bin
cp /opt/homebrew/bin/dezoomify-rs ~/path/to/workflow/bin/
```

---

## Alfred workflow setup

Build the workflow in Alfred with these objects, connected in order:

### 1 — Hotkey trigger
- **Type**: Hotkey (pick whatever shortcut you like)
- **Argument**: `Selection in macOS`
  *(This tells Alfred to copy the currently selected text and pass it as
  `{query}` before the workflow runs — no JS injection needed.)*

### 2 — Run Script (get browser info)
- **Type**: Run Script
- **Language**: `/bin/bash`
- **Script**:
  ```bash
  osascript -l JavaScript ./get_browser_info.js
  ```
- **Output**: leave as default (passes JSON string to next step)

> **Note**: Alfred runs scripts with the workflow folder as the working
> directory, so `./get_browser_info.js` resolves correctly.

### 3 — JSON to Variables
*(Alfred 5 utility object)*
- Parses the JSON from step 2 into workflow variables
- This creates: `{var:url}`, `{var:title}`, `{var:selected_text}`

### 4 — Set Variables (pass selected_text from hotkey)
- Add a variable: `selected_text = {var:selected_text}`
  *(The JXA script reads the clipboard for this, but belt-and-braces.)*

### 5 — Run Script (dezoomify + save)
- **Type**: Run Script
- **Language**: `/usr/bin/python3`
- **Script**:
  ```bash
  python3 ./dezoomify_save.py
  ```
- **Environment variables** (set in the script object or in User Config):

  | Variable | Default | Notes |
  |---|---|---|
  | `url` | `{var:url}` | Set automatically from step 3 |
  | `page_title` | `{var:title}` | Set automatically from step 3 |
  | `selected_text` | `{var:selected_text}` | Set automatically from step 3 |
  | `save_folder` | `~/Pictures/dezoomify` | Override in User Config |
  | `image_format` | `jpg` | `jpg` or `png` |
  | `dezoomify_bin` | *(auto-detected)* | Set if binary is in a non-standard location |
  | `max_megapixels` | *(empty = full res)* | Cap output size, e.g. `200` for ~14K×14K max |

### 6 — Post Notification
- **Title**: `Dezoomify Grab`
- **Text**: `{query}` (the Python script outputs the saved filename)

---

## User Configuration (Alfred 5)

In Alfred 5 you can expose settings as workflow User Configuration fields:

1. Open the workflow → click the `[x]` Variables icon (top right)
2. Add:
   - `save_folder` — type: File, default: `~/Pictures/dezoomify`
   - `image_format` — type: Select, options: `jpg / png`, default: `jpg`
   - `max_megapixels` — type: Text, default: `200` (recommended; leave blank for full resolution)
   - `dezoomify_bin` — type: Text, leave blank (auto-detect)

**About max_megapixels**: some museum images are enormous (the National Gallery's
Turner is 47,628 × 31,126 pixels = 1.48 gigapixels, ~22,000 tiles). Setting
`max_megapixels` to `200` caps output at ~14K×14K — plenty for screen or print —
and downloads in under a minute instead of 10+.

When `max_megapixels` is set, the `-l` (largest) flag is NOT passed to
dezoomify-rs, so `--max-width` / `--max-height` can select the appropriate zoom
level. When it's empty, `-l` is used for the largest available.

---

## What gets saved

For each grabbed image, two files are written to `save_folder`:

```
~/Pictures/dezoomify/
  My Painting Title.jpg
  My Painting Title.json    ← metadata sidecar
```

The JSON sidecar contains:
```json
{
  "source_url": "https://www.nationalgallery.org.uk/paintings/...",
  "tile_url": "https://www.nationalgallery.org.uk/server.iip?FIF=/fronts/N-0508-...tif",
  "page_title": "Turner — Ulysses deriding Polyphemus",
  "notes": "Any text you had selected when you triggered the workflow",
  "saved_at": "2026-05-17T14:30:00.123456",
  "image_file": "My Painting Title.jpg",
  "image_width": 4000,
  "image_height": 2613,
  "file_size_bytes": 2456789,
  "dezoomify_version": "2.13.0",
  "eagle_item_id": null
}
```

The `tile_url` field records which URL was actually passed to dezoomify-rs, when
it differs from the page URL (i.e. the scraper found a different endpoint). It's
`null` when the page URL worked directly.

---

## Supported sites

### Works directly (dezoomify-rs auto-detects)
- Google Arts & Culture (resolution capped by Google)
- Any site using standard IIIF, Zoomify, or DeepZoom with discoverable URLs

### Works via HTML scraping fallback
- **National Gallery, London** ✅ — IIPImage/IIIF tiles, TIFF path extracted from page source
- **Rijksmuseum** 🔧 — Micrio/IIIF tiles, in progress (currently picks up wrong image from related artworks)
- **NGV (National Gallery of Victoria)** ❌ — Zoomify tiles, not yet tested

### Manual paste required
- Any site where the tile URL isn't in the static HTML — open the browser's
  Network Inspector, zoom into the image, find the tile request, and paste it

---

## Debugging

The script logs to stderr, which is visible in:
- **Terminal**: inline with the output
- **Alfred**: open the workflow debug console (click the bug icon top-right in the workflow editor)

Log lines are prefixed `[dezoomify]` and show each step of the pipeline:
```
[dezoomify] Try 1: direct URL → https://...
[dezoomify] Failed: …none succeeded…
[dezoomify] Try 2: HTML scraping fallback
[dezoomify] Fetching HTML from https://...
[dezoomify] Running National Gallery scraper
[dezoomify]   Found TIFF via IIIF=: /fronts/N-0508-00-000032-XL-PYR.tif
[dezoomify] Trying candidate: NG IIPImage → https://...
[dezoomify] Success
```

---

## macOS permissions required

The workflow needs these permissions (macOS will prompt on first run):

- **Automation**: Safari and/or Google Chrome
  *(System Settings → Privacy & Security → Automation)*
- **Accessibility**: Alfred
  *(needed by Alfred's "Selection in macOS" hotkey option)*

---

## Troubleshooting

**"No supported browser is running"**
Alfred couldn't find Safari or Chrome. Make sure a browser window is open with
a tab loaded before invoking the workflow.

**dezoomify-rs fails / "No tiled image found"**
Not all pages host tiled images. dezoomify-rs works with IIIF, Zoomify,
DeepZoom, IIPImage and others. If the page uses a simple `<img>` tag, there's
nothing to dezoomify — just save the image directly.

**"File exists" error**
dezoomify-rs won't overwrite existing files. Delete the previous output file,
or the script will handle this automatically between retries.

**Download takes ages / times out**
The image might be enormous. Set `max_megapixels` to cap the output size (e.g.
`200` for ~14K×14K max). Some museum images are over a gigapixel.

**Both Safari and Chrome are running**
The JXA script currently favours Safari as a tie-break. If you usually want
Chrome, swap the order of the `safariRunning` / `chromeRunning` checks in
`get_browser_info.js` (lines near the bottom of the `else` block).

**File saved but image looks wrong / truncated**
Try changing `image_format` to `png`. Some tile sources don't transcode cleanly
to JPEG.

---

## Changelog

- **v1.2** — HTML scraping fallback with site-specific scrapers (National
  Gallery confirmed working). Retry logic with cleanup between attempts. Manual
  URL paste dialog as last resort. Fixed `-l` / `--max-width` mutual exclusion.
  Logging to stderr. `tile_url` field in metadata sidecar.
- **v1.1** — Extended metadata: dezoomify-rs version, image dimensions + file
  size (via sips), parsed title components, eagle_item_id placeholder. Added
  max_megapixels for size limiting.
- **v1.0** — Initial release.
