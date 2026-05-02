# dezoomify-alfred — v1.0

Alfred workflow to grab tiled images (IIIF, Zoomify, DeepZoom, etc.) from the
current browser tab using [dezoomify-rs](https://github.com/lovasoa/dezoomify-rs).

Saves the full-resolution image plus a JSON metadata sidecar to a folder you
configure. Works with Safari and Chrome.

---

## Files

| File | Purpose |
|---|---|
| `get_browser_info.js` | JXA script — gets URL, page title, selected text |
| `dezoomify_save.py` | Python script — runs dezoomify-rs, prompts for filename, saves files |
| `bin/dezoomify-rs` | Optional: bundled binary (see below) |

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
  osascript -l JavaScript "$alfred_workflow_cache/../../../info.plist" || \
  osascript -l JavaScript ./get_browser_info.js
  ```
  Simpler version (if script is in the workflow folder):
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

If you are on Alfred 4 instead, use two **Arg and Vars** steps, or pass the
raw JSON as `$json_output` and have the Python script parse `sys.argv[1]`.

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

### 6 — Post Notification
- **Title**: `Dezoomify Grab`
- **Text**: `{query}` (the Python script outputs the saved filename)

---

## User Configuration (Alfred 5)

In Alfred 5 you can expose `save_folder` and `image_format` as workflow User
Configuration fields so they're editable without opening the workflow:

1. Open the workflow → click the `[x]` Variables icon (top right)
2. Add:
   - `save_folder` — type: File, default: `~/Pictures/dezoomify`
   - `image_format` — type: Select, options: `jpg / png`, default: `jpg`
   - `dezoomify_bin` — type: Text, leave blank (auto-detect)

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
  "source_url": "https://example-museum.org/viewer/12345",
  "page_title": "Vermeer — Girl with a Pearl Earring",
  "notes": "Any text you had selected when you triggered the workflow",
  "saved_at": "2026-05-02T14:30:00.123456",
  "image_file": "My Painting Title.jpg"
}
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
DeepZoom, and a handful of other formats. If the page uses a simple `<img>`
tag, there's nothing to dezoomify — just save the image directly.

**Both Safari and Chrome are running**  
The JXA script currently favours Safari as a tie-break. If you usually want
Chrome, swap the order of the `safariRunning` / `chromeRunning` checks in
`get_browser_info.js` (lines near the bottom of the `else` block).

**File saved but image looks wrong / truncated**  
Try changing `image_format` to `png`. Some tile sources don't transcode cleanly
to JPEG.

---

## Possible next steps

- Eagle.app integration: import the saved image directly via Eagle's local API
  (`localhost:41595`) and attach the metadata as tags
- Bookmarklet version: trigger from the browser without Alfred installed
- Batch mode: grab all tiled images linked from a page
