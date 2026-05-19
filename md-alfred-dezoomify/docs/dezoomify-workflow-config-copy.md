# Dezoomify-nb

Get tiled images (IIIF, Zoomify, DeepZoom, IIPImage, etc.) plus any text selected on the current browser tab using [dezoomify-rs](https://github.com/lovasoa/dezoomify-rs).

Saves a stitched image plus a JSON metadata sidecar to a folder you configure. Works with Safari and Chrome.

## Setup

Install [dezoomify-rs](https://github.com/lovasoa/dezoomify-rs) via Homebrew:

```zsh
brew install dezoomify-rs
```

Grant macOS Automation permission for your browser(s) when prompted on first run (System Settings → Privacy & Security → Automation).


## Usage

1. Select any relevant text (eg. title, artist info and other metadata you might want to use in a citation later) on the page containing a tiled image. [Try this one](https://www.nationalgallery.org.uk/paintings/paolo-uccello-the-battle-of-san-romano))
2. Use the Hotkey or keyword `dezoomify` to get the image
3. The image and a JSON file containing metadata and the text selected will be saved in the folder you set in the workflow options.


## User Config

`save_folder` Where to save images. Set in Workflow configuration. Default `~/Pictures/dezoomify` 

`image_format` File type for saved images:`jpg` or `png`. jpg may have distortions, in which case use png. Default `jpg'.

`max_megapixels` Caps the image output size in megapixels. `20` for ~4500x4500px image, `200` for ~14K×14K pixels max. Empty = full resolution, which might be HUGE. Default: `20` 

`dezoomify_bin` *(auto-detected)*. Advanced setting: only us this if your dezoomify-rs binary is in a non-standard location; leave blank for autodetect.

### Intellectual Property and Copyright of Images

Images on the open web are subject to copyright law in the same manner as any other creative work; there is no guarantee that an image is legally available for re-use just because it is freely accessible on the web. It is your responsibility to check your intended use of the image is permitted under copyright law in your locality, or to clear your usage with the rights owner.

---


## How it works

1. **Try direct**: passes the browser URL to dezoomify-rs, which tries all its
   built-in dezoomers (IIIF, Zoomify, DeepZoom, IIPImage, etc.)
2. **Scrape fallback**: if that fails, fetches the page HTML and runs
   site-specific scrapers to find tile URLs hidden in JavaScript
3. **Manual paste**: if scraping finds nothing, shows a dialog where you can
   paste a tile URL from the browser's Network Inspector
4. Saves the image + JSON metadata sidecar to your configured folder

**v1.2 adds an HTML scraping fallback**: when dezoomify-rs can't auto-detect the
tiled image from the page URL (common on museum sites that load viewers via
JavaScript), the script fetches the page source and extracts tile URLs using
site-specific scrapers. Currently supports the National Gallery (London), with
Rijksmuseum and NGV in progress.

More information in the [GitHub README](https://github.com/mildlydiverting/md-tools/tree/main/md-alfred-dezoomify)

---

## Dependencies

**[dezoomify-rs](https://github.com/lovasoa/dezoomify-rs)** must be installed. (It should be bundled in the `bin` folder within this workflow, but I am new to this...)


The Python script looks for it in this order:
1. `./bin/dezoomify-rs` inside the workflow folder (bundled)
2. `/opt/homebrew/bin/dezoomify-rs` (Homebrew, Apple Silicon)
3. `/usr/local/bin/dezoomify-rs` (Homebrew, Intel)
4. Anywhere on `$PATH`