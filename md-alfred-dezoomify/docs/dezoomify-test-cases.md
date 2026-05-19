# Dezoomify Test Cases & Site Research

Reference document for testing dezoomify-rs Alfred workflow against museum/gallery collection pages.
Tracks which sites work, which fail, what tile technology each uses, and what approach to take for fixes.

**Last updated**: 2026-05-18

---

## The dezoomify ecosystem

Three tools, different layers — understanding what exists avoids reinventing things.

### dezoomify-rs (Rust CLI — what our Alfred workflow uses)

Built-in dezoomers: Google Arts & Culture, Zoomify, DeepZoom (DZI/Seadragon), IIIF, Zoomify PFF, krpano, IIPImage, NYPL, generic (URL template with `{{X}}`/`{{Y}}`), custom YAML.

- Repo: https://github.com/lovasoa/dezoomify-rs
- Docs on custom YAML: https://github.com/lovasoa/dezoomify-rs/wiki/Usage-example-for-the-custom-YAML-dezoomer
- DeepWiki ref: https://deepwiki.com/lovasoa/dezoomify-rs/3.6-custom-and-generic-formats

### dezoomify (JS web app)

Has some **site-specific dezoomers the Rust version doesn't**:
- `nationalgallery.js` — National Gallery's own format
- `xlimage.js` — Italian company format (used on several sites)
- `topviewer.js` — TopViewer format
- `fsi.js` — FSI Server
- `vls.js` — VLS viewer
- Picturae (several Dutch sites)

Also has: zoomify, seadragon (DeepZoom), iipimage, zoomify-pff, iiif, krpano, generic, automatic.

- Repo: https://github.com/lovasoa/dezoomify
- Dezoomers source: https://github.com/lovasoa/dezoomify/tree/master/dezoomers
- How to add a new site: https://github.com/lovasoa/dezoomify/wiki/How-to-add-support-for-a-new-website

### dezoomify-extension (browser extension)

Intercepts network requests and pattern-matches URLs to find tile/manifest endpoints. This is what finds the hidden IIIF/Zoomify/DZI URL that isn't in the page URL. The Chrome version is unmaintained (Manifest V2); a V3 fork exists at https://github.com/jbenton/dezoomify-extension-chromefix.

- Repo: https://github.com/lovasoa/dezoomify-extension
- Firefox: https://addons.mozilla.org/en-US/firefox/addon/dezoomify/
- Chrome V3 fork: https://chromewebstore.google.com/detail/dezoomify-v3/phjngidoalpcjbhgkdopmajfimmaocde

### What this means for us

Our Alfred workflow currently passes the browser URL straight to dezoomify-rs. When that fails, we have three possible fix strategies per site:

1. **Scraper** — Python fetches page HTML, extracts the tile/manifest URL, retries dezoomify-rs with that. Good for sites where the IIIF/Zoomify URL is in the page source but not the page URL.
2. **Custom YAML** — Write a `.yaml` tile definition. Good for sites with predictable tile URL patterns that dezoomify-rs doesn't auto-detect. Requires knowing tile dimensions per-image (so still needs a lightweight metadata extractor).
3. **Port a JS dezoomer** — Some JS dezoomers handle site-specific quirks (National Gallery, XLimage). Could port the logic to Python for our fallback, or contribute a Rust dezoomer upstream.

---

## Test cases

### Status key

| Status | Meaning |
|--------|---------|
| ✅ WORKS | dezoomify-rs handles the page URL directly |
| ⚠️ WORKS-INDIRECT | Works if you give it the manifest/tile URL, not the page URL |
| ❌ FAILS | dezoomify-rs can't find a dezoomer |
| 🔲 UNTESTED | Not yet tested |
| 🚫 NOT-ZOOMABLE | Site doesn't serve tiled/zoomable images |

### Google Arts & Culture

Dezoomify-rs has a dedicated GAC dezoomer. Generally works from page URLs, but Google caps resolution.

| URL | Status | Notes |
|-----|--------|-------|
| https://artsandculture.google.com/asset/light-in-the-dark/ZQFouDGMVmsI2w | ✅ WORKS | Documented known-good. Pesenti, "Light in the Dark" |
| https://artsandculture.google.com/asset/leichtes-light-kandinsky-vassily/BgH3g-qr8YpCGA | ✅ WORKS | Kandinsky, "Leichtes (Light)" |
| https://artsandculture.google.com/asset/ingres's-violin-man-ray/kQGJ3YIoasGh0A | ✅ WORKS | Man Ray, "Ingres's Violin" |
| https://artsandculture.google.com/asset/madame-x-madame-pierre-gautreau-john-singer-sargent/XQFBdVEh0NHo0A | ✅ WORKS  | Sargent, "Madame X" |
| https://artsandculture.google.com/asset/horse-study-after-george-stubbs-anatomy-of-the-horse-clara-drummond/IQHEEIRr5uvO7A | ✅ WORKS  | Clara Drummond, Horse Study |

### Rijksmuseum

Uses Micrio (`iiif.micr.io`) for IIIF delivery. The Micrio image ID is a short code not derivable from the page URL — needs network inspector or page source scraping.

| URL | Status | Notes |
|-----|--------|-------|
| https://www.rijksmuseum.nl/en/collection/object/Nude-Woman-Lying-on-a-Pillow--6af483682af3df3a835a526f7beb07f3 | ❌ FAILS | Tested 2 May. Tile URL pattern: `iiif.micr.io/{SHORTCODE}/...`. Shortcode not in page URL. |

**Fix approach**: Scraper — fetch page HTML, extract `iiif.micr.io/{ID}` from source, construct `https://iiif.micr.io/{ID}/info.json`, retry dezoomify-rs with IIIF dezoomer.

### National Gallery, London

The JS dezoomify has a dedicated `nationalgallery.js` dezoomer — suggests a non-standard format.

| URL | Status | Notes |
|-----|--------|-------|
| https://www.nationalgallery.org.uk/paintings/paolo-uccello-the-battle-of-san-romano | 🔲 UNTESTED | Uccello, Battle of San Romano. Check whether JS dezoomer logic is needed or if it's now IIIF. |
| Woman with a Cat, Edouard Manet - works using alfred workflow, fails in command line. |

**Fix approach**: Test first, then check whether the JS dezoomer's logic is still relevant or if NG has migrated to standard IIIF. If non-standard, consider porting `nationalgallery.js`.

### National Galleries of Scotland

Listed as supported by dezoomify-extension.

| URL | Status | Notes |
|-----|--------|-------|
| https://www.nationalgalleries.org/art-and-artists/42229 | 🔲 UNTESTED | |

### NGV (National Gallery of Victoria)

Uses Zoomify via `content.ngv.vic.gov.au`. Image ID (`Fd104934` etc.) is not derivable from the collection page URL (`/work/3867/`).

| URL | Status | Notes |
|-----|--------|-------|
| https://www.ngv.vic.gov.au/explore/collection/work/3867/ | ❌ FAILS | Constable, "The Quarters behind Alresford Hall". Tested 2 May. |

**Direct tile URL found**: `https://content.ngv.vic.gov.au/col-images/zooms/Fd104934/ImageProperties.xml` (untested — bare folder version failed).

**Fix approach**: Scraper — extract Zoomify base URL from page source.

### Tate

| URL | Status | Notes |
|-----|--------|-------|
| https://www.tate.org.uk/art/artworks/johnson-young-man-in-green-t16376 | 🔲 UNTESTED | Claudette Johnson, "Young Man in Green" |

### Barnes Foundation


| URL | Status | Notes |
|-----|--------|-------|
| https://collection.barnesfoundation.org/objects/5663/Young-Woman-Writing-(Jeune-femme-ecrivant)/ | 🔲 UNTESTED | Pierre Bonnard, Young Woman Writing (Jeune femme écrivant) |

### Met Museum

Has a public API (`metmuseum.github.io`). Large images may be served via IIIF or direct download.

| URL | Status | Notes |
|-----|--------|-------|
| https://www.metmuseum.org/art/collection/search/435809 | 🔲 UNTESTED | Check if zoomable or just large JPEG download. |

### Art Institute of Chicago

Has rich HTML microdata (from structured data audit). Public API available.

| URL | Status | Notes |
|-----|--------|-------|
| https://www.artic.edu/artworks/216746/cat | ✅ WORKS| From dezoomify-rs GitHub issues |
| https://www.artic.edu/artworks/103887/a-young-lady-with-a-parrot | ✅ WORKS | |

**Fix approach**: AIC uses IIIF — check whether manifest URL is discoverable from page source or API. Fixed a manifest issue where dezoomify was not seeing the manifest in python.

### Harvard Art Museums

Public API available. From structured data audit.

| URL | Status | Notes |
|-----|--------|-------|
| https://curiosity.lib.harvard.edu/daguerreotypes-at-harvard/catalog/17-HUAM160264_URN-3:HUAM:LEG002372_DYNMC | ❌ FAILS | From dezoomify-rs issues. Harvard library IIIF. Detected by IIF plugin https://mps.lib.harvard.edu/assets/images/drs:43154096/info.json |
| https://harvardartmuseums.org/collections/object/299848 | 🔲 UNTESTED | |

### Van Gogh Museum

| URL | Status | Notes |
|-----|--------|-------|
| https://www.vangoghmuseum.nl/en/collection/s0468N1996 | ❌ FAILS | Odilon Redon, "Roses in a Vase on a Small Table". From issues. |

### Wellcome Collection

| URL | Status | Notes |
|-----|--------|-------|
| https://wellcomecollection.org/works/zs6gser7/images?id=c7hxpemj | ✅ WORKS | Likely IIIF — Wellcome uses IIIF extensively. |
| https://wellcomecollection.org/works/an4bpesp/items | ✅ WORKS | Likely IIIF — Wellcome uses IIIF extensively. |

### V&A (Victoria and Albert Museum)

| URL | Status | Notes |
|-----|--------|-------|
| https://collections.vam.ac.uk/item/O685128/9-the-end-of--drawing-louis-wain/ | 🔲 UNTESTED | Louis Wain drawing |

### MKG Hamburg

| URL | Status | Notes |
|-----|--------|-------|
| https://www.mkg-hamburg.de/en/object/mkg-e00240258 | 🔲 UNTESTED | |

### Courtauld Gallery

| URL | Status | Notes |
|-----|--------|-------|
| https://gallerycollections.courtauld.ac.uk/object-d-1952-rw-219 | ❌ FAILS | |

### Frick Collection

| URL | Status | Notes |
|-----|--------|-------|
| https://collections.frick.org/objects/100/sir-thomas-more?ctx=60f15eabaf5ab42062d92a044cd5fb556130f057&idx=7 | ❌ FAILS | |

### Leopold Museum

| URL | Status | Notes |
|-----|--------|-------|
| https://onlinecollection.leopoldmuseum.org/objekt/539-sitzender-mannerakt-selbstdarstellung/#objektdaten | 🚫 NOT-ZOOMABLE | Confirmed: not a zoomable image. |

### Danish Royal Library (KB.dk)

| URL | Status | Notes |
|-----|--------|-------|
| https://digitalesamlinger.kb.dk/pamphlets/dasmaa/2008/feb/daellsvarehus/object74001/en/ | 🔲 UNTESTED | Pamphlet collection |

### ThULB (Jena University Library)

| URL | Status | Notes |
|-----|--------|-------|
| https://collections.thulb.uni-jena.de/rsc/viewer/HisBest_derivate_00004529/BE_1110_0593.tif | ❌ FAILS | From issues |


### SMK National Gallery of Denmark https://www.smk.dk

| URL | Status | Notes |
|-----|--------|-------|
| https://open.smk.dk/en/artwork/image/KMS3402?q=cat | ❌ FAILS | |

### Known-good direct tile URLs (for debugging)

These bypass the "find the manifest" problem — useful for testing dezoomify-rs itself.

| URL | Type | Notes |
|-----|------|-------|
| https://manifests.collections.yale.edu/ycba/obj/5005 | IIIF manifest | Yale YCBA. Used in original test script. Not a collection page. |
| https://content.ngv.vic.gov.au/col-images/zooms/Fd104934/ImageProperties.xml | Zoomify | NGV Constable. Untested. |

---

## Testing workflow

### For each URL, run:

```zsh
# 1. Try dezoomify-rs directly with the page URL
dezoomify-rs "{URL}" /tmp/test_output.jpg

# 2. If that fails, check what the extension would find:
#    Open the page in browser with dezoomify-extension active
#    Note what URLs it detects

# 3. View page source / network inspector for:
#    - IIIF: info.json or manifest.json URLs
#    - Zoomify: ImageProperties.xml or TileGroup paths
#    - DeepZoom: .dzi file URLs
#    - Micrio: iiif.micr.io/{ID} patterns
#    - OpenSeadragon config objects
#    - Any other tile URL patterns

# 4. If a tile URL is found, test it directly:
dezoomify-rs "{TILE_URL}" /tmp/test_output.jpg

# 5. Update this file with results
```

### Recording results

When testing, update the status and add to the notes:
- What tile technology the site uses (IIIF, Zoomify, DeepZoom, Micrio, OpenSeadragon, etc.)
- Whether the tile URL is discoverable from page source (static HTML) or only via JS execution
- The direct tile/manifest URL if found
- Any Referer or auth headers needed

---

## Site technology research log

Use this section to record findings as you investigate each site. Format:

```
### site-name (date investigated)

**Tile tech**: [IIIF / Zoomify / DeepZoom / Micrio / OpenSeadragon / unknown]
**Tile URL discoverable from HTML?**: [yes / no / needs JS]
**Direct tile URL pattern**: [URL pattern]
**Referer needed?**: [yes: {url} / no / unknown]
**Existing dezoomer?**: [dezoomify-rs native / JS dezoomify {filename} / none]
**Recommended fix approach**: [scraper / custom YAML / port JS dezoomer / upstream PR / none needed]
**Notes**: [anything else]
```

### rijksmuseum.nl (2 May 2026)

**Tile tech**: IIIF via Micrio (iiif.micr.io)
**Tile URL discoverable from HTML?**: Yes — `iiif.micr.io/{SHORTCODE}` appears in page source for related works
**Direct tile URL pattern**: `https://iiif.micr.io/{SHORTCODE}/info.json`
**Referer needed?**: Unknown
**Existing dezoomer?**: dezoomify-rs IIIF (once you have the info.json URL)
**Recommended fix approach**: Scraper — extract Micrio shortcode from page HTML, construct info.json URL
**Notes**: Shortcode is not derivable from the collection page URL. Need to parse page source.

### ngv.vic.gov.au (2 May 2026)

**Tile tech**: Zoomify
**Tile URL discoverable from HTML?**: Likely yes — found via network inspector
**Direct tile URL pattern**: `https://content.ngv.vic.gov.au/col-images/zooms/{ID}/ImageProperties.xml`
**Referer needed?**: Unknown
**Existing dezoomer?**: dezoomify-rs Zoomify (once you have the ImageProperties.xml URL)
**Recommended fix approach**: Scraper — extract Zoomify base URL from page source
**Notes**: Image ID (e.g. `Fd104934`) doesn't correlate with collection page URL (`/work/3867/`).
