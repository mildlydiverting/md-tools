# Alfred workflow setup — building from source

These instructions are for wiring up the workflow objects in Alfred if you're building from source rather than installing a pre-built `.alfredworkflow` file. If you installed the workflow normally, you don't need any of this.


## Workflow objects

Connect these objects in order:

### 1 — Hotkey trigger

- **Type**: Hotkey (default <kbd>⌥</kbd><kbd>D</kbd>, or whatever you prefer)
- **Argument**: `Selection in macOS`

This tells Alfred to capture the currently selected text and pass it as `{query}` before the workflow runs.

### 2 — Run Script (get browser info)

- **Type**: Run Script
- **Language**: `/bin/bash`
- **Script**:
  ```bash
  osascript -l JavaScript ./get_browser_info.js
  ```
- **Output**: leave as default (passes JSON string to next step)

Alfred runs scripts with the workflow folder as the working directory, so `./get_browser_info.js` resolves correctly.

### 3 — JSON to Variables

Alfred 5 utility object. Parses the JSON from step 2 into workflow variables: `{var:url}`, `{var:title}`, `{var:selected_text}`.

### 4 — Set Variables

Pass selected text through: `selected_text = {var:selected_text}`.

The JXA script also reads the clipboard for this, but belt-and-braces.

### 5 — Run Script (dezoomify + save)

- **Type**: Run Script
- **Language**: `/usr/bin/python3`
- **Script**:
  ```bash
  python3 ./dezoomify_save.py
  ```

Environment variables (set in the script object or in User Configuration):

| Variable | Default | Notes |
|---|---|---|
| `url` | `{var:url}` | Set automatically from step 3 |
| `page_title` | `{var:title}` | Set automatically from step 3 |
| `selected_text` | `{var:selected_text}` | Set automatically from step 3 |
| `save_folder` | `~/Pictures/dezoomify` | Override in User Configuration |
| `image_format` | `jpg` | `jpg` or `png` |
| `dezoomify_bin` | *(auto-detected)* | Set if binary is in a non-standard location |
| `max_megapixels` | `20` | Cap output size; leave empty for full resolution |

### 6 — Post Notification

- **Title**: `Dezoomify Grab`
- **Text**: `{query}` (the Python script outputs the saved filename)

## User Configuration fields

In Alfred 5, expose these as workflow User Configuration fields (click the `[x]` Variables icon, top right):

| Field | Type | Default | Notes |
|---|---|---|---|
| `save_folder` | File | `~/Pictures/dezoomify` | Where images and sidecars are saved |
| `image_format` | Select (`jpg` / `png`) | `jpg` | |
| `max_megapixels` | Text | `20` | `20` ≈ 4500 × 4500 px; `200` ≈ 14K × 14K; blank = full resolution |
| `dezoomify_bin` | Text | *(blank)* | Leave blank for auto-detection |

## Bundling the binary (work in progress)

To make the workflow portable or shareable, you can bundle the dezoomify-rs binary:

```zsh
mkdir -p ~/path/to/workflow/bin
cp /opt/homebrew/bin/dezoomify-rs ~/path/to/workflow/bin/
```

The script checks `./bin/dezoomify-rs` first, so a bundled binary takes priority over a Homebrew install.

**Note on licensing**: dezoomify-rs is licensed under [GPL-3.0](https://github.com/lovasoa/dezoomify-rs/blob/master/LICENSE). If you distribute a workflow with the binary bundled, you must include the GPL-3.0 licence text and point to the dezoomify-rs source code.
