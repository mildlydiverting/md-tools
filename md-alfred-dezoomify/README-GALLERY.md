# Dezoomify

Grab full-resolution tiled images (and metadata) from museum websites and image viewers.

## Setup

Install [dezoomify-rs](https://github.com/lovasoa/dezoomify-rs) via Homebrew:

```zsh
brew install dezoomify-rs
```

Grant macOS Automation permission for your browser(s) when prompted on first run (System Settings → Privacy & Security → Automation).

## Usage

Grab a full-resolution tiled image from the current browser tab via the `dezoomify` keyword. Select any text on the page first (title, artist, date — anything useful for citation) and it will be saved alongside the image.

![Searching for dezoomify](images/keyword.png)

* <kbd>↩</kbd> Grab the image from the frontmost browser tab.

Configure the Hotkey (default <kbd>⌥</kbd><kbd>D</kbd>) to grab directly from Safari or Chrome without opening Alfred.

The workflow will prompt you for a file name (prepopulated with selected text)

![Paste dialog for file name](images/save-as.png)

The workflow detects IIIF, Zoomify, DeepZoom, and IIPImage viewers automatically. If the tiled image can't be found in the page source, a dialog appears where you can paste a tile URL from the browser's Network Inspector. Open the browser Network Inspector, zoom into the image, and look for tile requests containing server.iip, info.json, or ImageProperties.xml.

![Paste dialog for manual tile URL](images/request-tiles-url.png)


Each grab saves two files: the image and a JSON metadata sidecar containing the source URL, page title, image dimensions, and any text you had selected.

```
~/Pictures/dezoomify/
  Lime Pot in the Shape of a Cat.jpg
  Lime Pot in the Shape of a Cat.json
```

Set `max_megapixels` in the Workflow's Configuration to cap output size. The default of `20` gives roughly 4500 × 4500 pixels; set it to `200` for ~14K × 14K. Leave it empty for full resolution — but be warned, some museum images exceed a gigapixel and will take a very long time to download.

## Supported sites

The workflow handles most tiled-image viewers out of the box. Sites using standard IIIF, Zoomify, or DeepZoom with discoverable URLs work directly. For sites that load viewers via JavaScript, a scraping fallback extracts tile URLs from the page source.

Currently confirmed: National Gallery (London). Rijksmuseum and NGV (National Gallery of Victoria) scrapers are in progress. Google Arts & Culture works directly but resolution is capped by Google.

For any site where the tile URL isn't in the static HTML, open the browser's Network Inspector, zoom into the image, find the tile request, and paste it when prompted.

## Intellectual property and copyright

Images on the open web are subject to copyright law in the same way as any other creative work. There is no guarantee that an image is legally available for re-use just because it is freely accessible online. It is your responsibility to check that your intended use is permitted under copyright law in your locality, or to clear your usage with the rights owner.

## Troubleshooting

If dezoomify-rs reports "No tiled image found", the page may not host a tiled image at all — some sites use a simple `<img>` tag, in which case there's nothing to dezoomify.

If a download takes a very long time or times out, set `max_megapixels` in the Workflow's Configuration to limit the output size.

If the saved image looks wrong or truncated, try changing `image_format` to `png` in the Workflow's Configuration. Some tile sources don't transcode cleanly to JPEG.

Debug output is visible in Alfred's workflow debug console (click the bug icon in the workflow editor). Log lines are prefixed `[dezoomify]` and show each step of the pipeline.

[Check GitHub for issues and more information](https://github.com/mildlydiverting/md-tools/tree/main/md-alfred-dezoomify).
